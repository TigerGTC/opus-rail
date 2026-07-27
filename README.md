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
  slice it's handed, so evidence-backed refutations bind, opinions on direction don't —
  the 4.8 orchestrator adjudicates from the full picture.
- **`worker`** (Sonnet) — mechanical bulk and read-heavy search, kept cheap.

Two ways to run it:

## 1. Full system (`full/`)

Hook-enforced. A model-conditional hook (`opus-rails.py`) injects the operating rules
only into sessions whose main loop is Opus — Sonnet/Haiku/Fable sessions pay nothing —
and re-injects after compaction. It includes a **routing check** that fires on
implementation-shaped prompts at the moment the routing decision is made. That check
exists because of a measured failure: with the delegation rule injected as prose only,
a live opus session implemented a 2-file task directly with zero dispatches; with the
routing check, the same class of task produced one properly scoped executor dispatch
and zero direct edits. Dispatch telemetry (`opus-rails.py stats`) reports the
delegation rate so the behavior stays measurable.

Install: see [`full/INSTALL.md`](full/INSTALL.md).

## 2. Skill only (`skill/`)

Distribution-friendly: no hooks, no settings surgery, nothing persistent. Copy one
skill folder, then run `/opus-rail` at the start of a session to switch it into the
same orchestration for the rest of that session. Same roles and rules, embedded in
the skill text; the trade is enforcement (the model follows instructions rather than
being re-prompted by hooks) and you re-run it each session.

Install: copy `skill/opus-rail/` into `~/.claude/skills/`, then run `/opus-rail`.

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
