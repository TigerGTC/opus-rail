#!/usr/bin/env python3
"""opus-rails — model-conditional guardrails, injected at the moment of risk.

Why this exists: Opus 5's measured failure profile (2026-07-26 session audit, receipts in
~/.claude/docs/opus-guardrails.md) is confident wrong claims, marketing-page sourcing,
own-record amnesia, uncounted-corpus design, and plan-scale drift — all violations of rules
that ALREADY sat in CLAUDE.md. Static prose does not prevent them, because they happen at
peak confidence. So the rails are injected event-conditionally (per session, on plan writes,
after web research, after compaction, on implementation-shaped prompts) and
MODEL-conditionally: Opus pays; Fable/Sonnet/Haiku sessions pay nothing.

Since the 2026-07-26 duo rework, the opus alias is pinned to Opus 4.8 and Opus 5 runs only
inside the executor/redteam agents (which carry their own baked-in rails, because hooks do
not fire in subagent contexts). The main-loop rails therefore now guard the 4.8
ORCHESTRATOR: rules 1-6 are retained as cheap epistemic insurance, and rules 7-8 + the
routing check are the delegation doctrine — the part empirically shown to need
point-of-decision injection, not prose.

The harness exposes no model field to hooks. Resolution order (Sol review, 2026-07-26):
  1. a FRESH statusline flag (~/.claude/.model-live/sess-<session_id>, mtime < 10 min) —
     the statusline receives model.id every render, so right after a /model switch this is
     the only source that already names the NEW model;
  2. transcript scan — the last non-sidechain assistant entry's message.model. This is the
     last OBSERVED main-loop model, not configuration: it lags a /model switch until the
     new model speaks. The sidechain filter is mandatory (subagent lines carry the
     subagent's model);
  3. any stale flag (session-keyed, then legacy cwd-keyed).

Subcommands (one per hook event, session-registry.py idiom):
  prompt      UserPromptSubmit      core rails once per session; ROUTING CHECK on
              implementation-shaped prompts (re-armed 20 min); also the compaction
              FALLBACK — if PreCompact left a marker, re-inject rails + re-read-the-goal
  plan        PreToolUse Edit|Write premise checklist on plans/**.md, once per file
  web         PostToolUse WebFetch|WebSearch  sourcing rail, re-armed after 45 min or compact
  dispatch    PreToolUse ^Agent$    observation only: log subagent dispatches for stats
  compact     SessionStart(compact) re-inject rails + re-read-the-goal; consumes the marker
  precompact  PreCompact            model-agnostic: drop the compaction marker (fallback
              path in case SessionStart(compact) does not fire in some harness version)

Known coverage boundaries (2026-07-26 audit): hooks do not fire inside subagent
(sidechain) contexts — rails, dep-guard, and destructive-guard are all absent there, so
those prohibitions are baked into the agent definitions (executor/redteam/worker.md)
instead. Headless --print sessions have no statusline, so the model flag is never
written and rails resolution fails on the first prompt (interactive sessions are
covered from the first render).

Every path exits 0: a hook that breaks the session is worse than a lesson unlearned.
"""
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

CFG = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
STATE = CFG / ".opus-rails"          # per-session markers; pruned after 7 days
FLAG_DIR = CFG / ".model-live"       # written by statusline.sh
PLAN_RE = re.compile(r"(^|/)(\.agents/)?plans?/.+\.md$")
TAIL_BYTES = 262144                  # transcript tail window, doubled once if no hit
TAIL_MAX = 2097152
FLAG_FRESH_S = 600                   # a statusline flag younger than this outranks the
                                     # transcript: right after /model the transcript still
                                     # names the OLD model, the statusline the new one
PRUNE_S = 7 * 24 * 3600

RAILS = """OPUS RAILS (model-conditional; injected because this session's main loop is Opus. Rules 1-6 are epistemic guards derived from an audited failure profile — receipts in ~/.claude/docs/opus-guardrails.md; rules 7-8 are the orchestration doctrine: 4.8 drives, Opus 5 executes and red-teams):
1. Mechanism claims need a run, not plausibility. Before stating "X happens because Y", verify Y against the actual code/pipeline this session, or write [unverified].
2. External facts come from authoritative surfaces — spec/openapi.json/llms.txt/source — never a marketing page or memory. If no authority was opened this session, the claim carries [unverified].
3. Consult your own record before deciding: MEMORY.md, the repo's plans and findings docs. If a claim contradicts something already recorded, resolve the contradiction first — do not proceed past it.
4. Count before designing. Any plan built on a corpus/dataset/asset set starts by counting its DISTINCT items, not its files or frames.
5. A user answer that widens scope is a checkpoint, not permission. Before building on it, restate the session goal in one line and check the widened scope against the evidence already recorded — ambition absorbed without that check is how a plan died same-day here.
6. Decisions carry the measurement that forced them. A decision carrying only reasoning is a hypothesis and belongs in Open questions.
7. You are the orchestrator, not the implementer. Route each TASK before touching it — not once per session: implementation, debugging, and focused review go to `executor` (Opus 5); mechanical bulk and read-heavy search go to `worker` (Sonnet). A dispatch is scoped or it is rework: single objective, exact file paths, constraints that apply, the command that must pass, and the return format expected. Implement directly only when the whole change is one trivial file — a second file, real debugging, or design judgment means dispatch. This is the owner's measured decision (better results AND a leaner orchestrator context; token cost accepted) — it supersedes the general one-clean-pass cost rule inside opus sessions. You personally: frame, adjudicate against the real code, verify, commit, update state files.
8. Ideas, plans, designs, and architectural decisions get an adversarial pass BEFORE being presented or acted on: dispatch the `redteam` agent (Opus 5) with the proposal and enough context to attack it, then adjudicate its findings yourself. Its findings are ADVISORY — it sees only the slice you handed it, and you hold the full context and history. A premise it REFUTED with evidence outranks your reasoning; its opinions on direction or scope do not — reject those from the fuller picture, stating in one line what context dissolves them. Accept only findings that survive your own check against the real code. Skip the pass only for trivial edits and pure lookups."""

PLAN_GUARD = ("PLAN-WRITE GUARD (Opus, once per plan file): before this plan is presented as "
              "ready — (a) COUNT the distinct items of any corpus/dataset/asset set a phase is "
              "built on; (b) verify each premise against the authoritative surface (spec/source), "
              "not a secondary page; (c) grep earlier plans for decisions this one reverses and "
              "name each reversal explicitly with the new evidence that justifies it; (d) mark "
              "every Decision as measurement-backed or hypothesis — hypotheses move to Open "
              "questions; (e) state the likeliest way this plan is falsified within a week; "
              "(f) dispatch the `redteam` agent (Opus 5) against the full plan text and "
              "adjudicate its findings before presenting. A plan was falsified same-day here "
              "for skipping exactly these.")

WEB_GUARD = ("SOURCING RAIL (Opus, once per session): marketing pages are not specs. Before "
             "asserting capabilities, limits, or pricing of an external system, open its "
             "authoritative surface (openapi.json, llms.txt, docs API, source). Claims sourced "
             "from anything else carry [unverified].")

COMPACT_NOTE = ("\nCONTEXT WAS JUST COMPACTED. Re-read the current goal and task list from "
                "their files before continuing — do not infer them from the summary alone. If "
                "a /goal is active, restate it in one line before the next action.")

EFFORT_NOTE = ("\n(Effort is %s: verification steps are the first thing reduced effort drops. "
               "Do not skip them — prefer flagging [unverified] over asserting.)")

ROUTE_NOTE = ("ROUTING CHECK (Opus, implementation-shaped turn): this turn looks like "
              "implementation. Either dispatch `executor` now — scoped: objective, exact "
              "paths, constraints, the command that must pass, return format — or state in "
              "one line why direct is right (trivial single-file only). Empirically, rails "
              "prose alone did not produce delegation at the point of action; this check "
              "exists because an opus session implemented a 2-file task directly with rule 7 "
              "in context. Delegating also keeps this context window lean.")

# Implementation-shaped prompt: imperative build verb present, not a question, not a
# slash command. Deliberately loose — the note is advisory and re-armed, not a gate.
IMPL_RE = re.compile(r"(?i)\b(implement|build|add|fix|create|write|refactor|rework|wire"
                     r"|debug|migrate|convert|optimi[sz]e|extend|integrate|rewrite)\b")
ROUTE_REARM_S = 20 * 60

DECISION_PAT = re.compile(r"(?i)(never|always|DECIDED|rejected|superseded|do not|must not)")
GREP_FILES = 4                       # newest sibling docs scanned for prior decisions
GREP_LINES = 8                       # max ground-truth lines injected


def _prior_decisions(plan_path):
    """Ground-truth injection (both red-teams converged on this): do the retrieval FOR the
    model and inject what it finds, instead of reminding it to look. Bounded scan of the
    newest sibling plan/doc files for decision-shaped lines."""
    try:
        d = Path(plan_path).parent
        if not d.is_dir():
            return ""
        sibs = sorted((q for q in d.glob("*.md") if str(q) != str(plan_path)),
                      key=lambda q: q.stat().st_mtime, reverse=True)[:GREP_FILES]
        out = []
        for q in sibs:
            for line in _read(q, 65536).splitlines():
                t = line.strip()
                if 20 < len(t) < 200 and DECISION_PAT.search(t):
                    out.append("%s: %s" % (q.name, t[:160]))
                    if len(out) >= GREP_LINES:
                        break
            if len(out) >= GREP_LINES:
                break
        if not out:
            return ""
        return ("\nPRIOR DECISIONS FOUND NEARBY (the hook grepped so you do not have to; "
                "name any this plan reverses):\n- " + "\n- ".join(out))
    except OSError:
        return ""


def _read(path, limit=None):
    try:
        with open(path, "rb") as f:
            if limit:
                f.seek(0, 2)
                size = f.tell()
                f.seek(max(0, size - limit))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


def _model_from_transcript(tp, limit=TAIL_BYTES):
    """Last observed main-loop model: the last non-sidechain assistant message's
    message.model in the transcript tail. NOTE: this is history, not configuration —
    after a /model switch it lags until the new model speaks, which is why a fresh
    statusline flag outranks it."""
    if not tp:
        return ""
    text = _read(tp, limit)
    if '"assistant"' not in text and limit < TAIL_MAX:
        text = _read(tp, TAIL_MAX)   # giant tool results can push assistants out of range
    for line in reversed(text.splitlines()):
        if '"assistant"' not in line:
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        m = ((d.get("message") or {}).get("model")) or ""
        if m and "synthetic" not in m:
            return m
    return ""


def _flag_paths(data):
    out = []
    sid = data.get("session_id")
    if sid:
        out.append(FLAG_DIR / ("sess-%s" % sid))
    cwd = data.get("cwd")
    if cwd:
        out.append(FLAG_DIR / hashlib.sha1(cwd.encode()).hexdigest()[:16])
    return out


def _model_from_flag(data, fresh_only=False):
    now = time.time()
    for p in _flag_paths(data):
        try:
            if fresh_only and now - p.stat().st_mtime > FLAG_FRESH_S:
                continue
            v = _read(p).strip()
        except OSError:
            continue
        if v:
            return v
    return ""


def _resolve(data):
    """(model, source). Source names which resolver answered — telemetry needs it because
    a detection layer that fails silently is a guardrail that lies about coverage."""
    m = _model_from_flag(data, fresh_only=True)
    if m:
        return m, "flag-fresh"
    m = _model_from_transcript(data.get("transcript_path"))
    if m:
        return m, "transcript"
    m = _model_from_flag(data)
    return m, ("flag-stale" if m else "unresolved")


def _is_opus(data):
    """Main-loop-only: subagent contexts (agent_id set) get no rails in v1. The agent_id
    contract is best-effort (observed in the harness payload builder, not documented) —
    if it were ever absent, the sidechain-filtered transcript scan still resolves the
    PARENT model, which is the intended question."""
    if data.get("agent_id"):
        return False
    return "opus" in _resolve(data)[0].lower()


def _marker(session_id, name):
    STATE.mkdir(parents=True, exist_ok=True)
    return STATE / ("%s.%s" % (session_id or "nosession", name))


def _claim(marker):
    """Atomically claim a once-marker. True exactly once per marker path."""
    try:
        fd = os.open(str(marker), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(int(time.time())).encode())
        os.close(fd)
        return True
    except OSError:
        return False


def _prune():
    now = time.time()
    try:
        for p in STATE.iterdir():
            if now - p.stat().st_mtime > PRUNE_S:
                p.unlink()
    except OSError:
        pass


LOG = CFG / ".opus-rails" / "injections.jsonl"


def _log(data, event, source):
    """Telemetry: a guardrail whose detection layer can fail silently needs a record that
    it fired. `rails-stats` summarizes this. Events prefixed `obs-` are observations
    (e.g. dispatches), not injections — stats reports them separately."""
    try:
        model, via = _resolve(data)
        with open(LOG, "a") as f:
            f.write(json.dumps({"ts": int(time.time()), "event": event,
                                "session": data.get("session_id"),
                                "resolved": model, "via": via,
                                "detail": source or None}) + "\n")
    except OSError:
        pass


def _emit_json(event, text):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": event, "additionalContext": text}}))


WEB_REARM_S = 15 * 60


def _consume_compact_marker(data):
    m = _marker(data.get("session_id"), "compacted")
    if not m.exists():
        return False
    try:
        m.unlink()
    except OSError:
        pass
    # a compaction also re-arms the web rail: the sourcing reminder was summarized away
    w = _marker(data.get("session_id"), "web")
    if w.exists():
        try:
            w.unlink()
        except OSError:
            pass
    return True


def _route_check(data):
    """Redteam-derived replacement for the (refuted) edit-count drift guard: intervene at
    the moment the routing decision is made — the user prompt — not after edits happened.
    Would have fired on the observed failure ('Implement the missing sub and ...')."""
    text = (data.get("prompt") or "").strip()
    if len(text) < 20 or text.startswith("/") or text.endswith("?"):
        return ""
    if not IMPL_RE.search(text):
        return ""
    m = _marker(data.get("session_id"), "route")
    try:
        if m.exists() and time.time() - m.stat().st_mtime < ROUTE_REARM_S:
            return ""
        m.write_text(str(int(time.time())))
    except OSError:
        return ""
    _log(data, "route", "")
    return "\n\n" + ROUTE_NOTE


def cmd_prompt(data):
    _prune()
    if not _is_opus(data):
        return
    shown = _marker(data.get("session_id"), "shown")
    effort = ((data.get("effort") or {}).get("level")) or ""
    extra = EFFORT_NOTE % effort if effort in ("low", "medium") else ""
    route = _route_check(data)
    if _consume_compact_marker(data):
        print(RAILS + extra + COMPACT_NOTE + route)
        _log(data, "prompt-compact", "")
        try:
            shown.write_text(str(int(time.time())))
        except OSError:
            pass
        return
    if _claim(shown):
        print(RAILS + extra + route)
        _log(data, "prompt", "")
    elif route:
        print(route.strip())


PLAN_REARM_S = 20 * 60


def cmd_plan(data):
    if not _is_opus(data):
        return
    tool = data.get("tool_name") or ""
    if tool == "ExitPlanMode":
        # Kimi finding: plan-mode plans never touch plans/*.md, so the file guard misses
        # an entire plan genre. Same checklist, keyed once per session.
        if _claim(_marker(data.get("session_id"), "plan.exitplanmode")):
            _emit_json("PreToolUse", PLAN_GUARD)
            _log(data, "plan-exitplanmode", "")
        return
    path = ((data.get("tool_input") or {}).get("file_path")) or ""
    if not PLAN_RE.search(path):
        return
    # Kimi finding: a plan's first write is a skeleton; premises arrive in later edits.
    # Forever-dedupe guards the wrong moment, so the guard re-arms per file after 20 min.
    key = "plan." + hashlib.sha1(path.encode()).hexdigest()[:12]
    m = _marker(data.get("session_id"), key)
    try:
        if m.exists() and time.time() - m.stat().st_mtime < PLAN_REARM_S:
            return
        m.write_text(path)
    except OSError:
        return
    _emit_json("PreToolUse", PLAN_GUARD + _prior_decisions(path))
    _log(data, "plan", "")


def cmd_web(data):
    if not _is_opus(data):
        return
    m = _marker(data.get("session_id"), "web")
    try:
        if m.exists() and time.time() - m.stat().st_mtime < WEB_REARM_S:
            return
        m.write_text(str(int(time.time())))
    except OSError:
        return
    _emit_json("PostToolUse", WEB_GUARD)
    _log(data, "web", "")


def cmd_compact(data):
    # Right after compaction the transcript still holds full history, so the normal
    # resolver applies; the flag is the fallback if the payload lacks a transcript.
    if not _is_opus(data):
        _consume_compact_marker(data)      # don't leave a stale marker for a later model
        return
    _consume_compact_marker(data)
    print(RAILS + COMPACT_NOTE)
    _log(data, "compact", "")
    # refresh (not clear): rails were JUST re-injected here, so `prompt` stays silent.
    try:
        _marker(data.get("session_id"), "shown").write_text(str(int(time.time())))
    except OSError:
        pass


def cmd_dispatch(data):
    """PreToolUse ^Agent$ — observation only, no injection. Records each subagent
    dispatch (with subagent_type) so `stats` can report the delegation rate; a routing
    rule whose usage can't be measured can't be tuned. Redteam review rejected active
    guards here: matcher must be ^Agent$ (Task* tools are unrelated), and the thin-prompt
    heuristic had 0/499 true positives on the historical dispatch corpus."""
    if not _is_opus(data):
        return
    sub = ((data.get("tool_input") or {}).get("subagent_type")) or "unspecified"
    _log(data, "obs-dispatch", sub)


def cmd_precompact(data):
    # Model-agnostic and unconditional: PreCompact fires BEFORE the summary exists, and
    # this must be cheap. The marker is consumed by SessionStart(compact) if that fires,
    # else by the next prompt — whichever comes first re-injects exactly once.
    try:
        _marker(data.get("session_id"), "compacted").write_text(str(int(time.time())))
    except OSError:
        pass


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    if cmd == "stats":
        try:
            lines = [json.loads(l) for l in _read(LOG).splitlines() if l.strip()]
        except ValueError:
            lines = []
        from collections import Counter
        inj = [l for l in lines if not l["event"].startswith("obs-")]
        obs = [l for l in lines if l["event"].startswith("obs-")]
        print("injections: %d  by-event: %s  by-source: %s"
              % (len(inj), dict(Counter(l["event"] for l in inj)),
                 dict(Counter(l.get("via") or "n/a" for l in inj))))
        print("dispatches: %d  by-agent: %s"
              % (len(obs), dict(Counter(l.get("detail") or "n/a" for l in obs))))
        return
    fn = {"prompt": cmd_prompt, "plan": cmd_plan, "web": cmd_web,
          "compact": cmd_compact, "precompact": cmd_precompact,
          "dispatch": cmd_dispatch}.get(cmd)
    if fn:
        fn(data)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # a hook that breaks the session is worse than a lesson unlearned
    sys.exit(0)
