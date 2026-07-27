# opus-rail

Claude Code orchestration where **Opus 4.8 drives and Opus 5 works**.

The premise, measured in real use: Opus 4.8 as the main-loop orchestrator follows
project doctrine, keeps a leaner context window, and produces a better working flow —
while Opus 5 is at its best inside tightly scoped, single-objective tasks. So this
setup pins the orchestrator to 4.8 and gives it three delegation lanes:

- **`executor`** (Opus 5) — the default destination for implementation: coding,
  debugging, test-writing, focused review. Dispatched per task with a full scope:
  objective, exact paths, constraints, the command that must pass, return format.
- **`redteam`** (Opus 5) — read-only adversarial reviewer, dispatched against ideas,
  plans, and designs *before* they're presented. Advisory by design: it sees only the
  slice it's handed, so the orchestrator adjudicates every finding from the full
  picture — a refutation whose evidence survives that check binds; opinions on
  direction never do.
- **`worker`** (Sonnet) — mechanical bulk and read-heavy search, kept cheap.

Two ways to run it:

## 1. Full system (`full/`)

Hook-driven. Nothing blocks — the hook injects the right rule at the moment it
matters, which measurement showed is what actually changes behavior. A
model-conditional hook (`opus-rails.py`) injects the operating rules
only into sessions whose main loop is Opus — non-Opus sessions pay nothing —
and re-injects after compaction. macOS/Linux only (hook paths and shell). It includes a **routing check** that fires on
implementation-shaped prompts at the moment the routing decision is made. That check
exists because of a measured failure: with the delegation rule injected as prose only,
a live opus session implemented a 2-file task directly with zero dispatches; with the
routing check, the same class of task produced one properly scoped executor dispatch
and zero direct edits. Telemetry (`opus-rails.py stats`) reports injection counts,
routing-check firings, and dispatch attempts by agent — enough to watch the
delegation trend and notice a dead guard (a dispatch is logged at pre-tool time,
so it counts attempts, not confirmed completions).

Install: see [`full/INSTALL.md`](full/INSTALL.md).

## 2. Skill only (`skill/`)

Distribution-friendly: no hooks, no settings surgery, nothing persistent. Copy one
skill folder, then run `/opus-rail` at the start of a session to switch it into the
same orchestration for the rest of that session. Same roles and rules, embedded in
the skill text; the trade is enforcement (the model follows instructions rather than
being re-prompted by hooks) and you re-run it each session.

Install (requires Claude Code ≥ 2.1.219 so the `opus`/`sonnet` model aliases resolve
as the skill assumes):

```bash
mkdir -p ~/.claude/skills && cp -R skill/opus-rail ~/.claude/skills/
```

Then run `/opus-rail` at the start of each session — or `/opus-rail plus` to also
enable the dispatched redteam lane (off by default in the skill variant for token
efficiency; in standard mode the orchestrator self-red-teams without a dispatch).

## Known boundaries (measured, 2026-07)

- **Hooks do not fire inside subagents.** Verified live: a `pip install` invocation
  inside a subagent ran with no hook interception. Any guard you rely on (dependency
  approval, destructive-command gating) must be written into the agent definitions —
  the ones here carry those prohibitions explicitly.
- **Headless `--print` sessions** have no statusline, so the model flag that makes
  first-prompt injection work is never written; rails resolve from the transcript
  starting with the second exchange. Interactive sessions are covered from the first
  render (see `full/statusline-flag-snippet.sh`).
- The rails text is opinionated and was derived from audited failure sessions on the
  author's machine; edit the rule text to taste, keep the mechanism.
- **The two variants are not fully independent**: the full system's env pin re-points
  the `opus` alias to 4.8 machine-wide, so the skill variant's `model: "opus"`
  subagent lanes would then resolve to 4.8 instead of Opus 5. Run one variant or the
  other, not both; the skill assumes an unpinned `opus` alias (Claude Code ≥ 2.1.219,
  where it resolves to Opus 5).
