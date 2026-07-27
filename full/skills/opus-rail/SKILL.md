---
name: opus-rail
description: >-
  Session control for the FULL opus-rail system (hook-enforced variant).
  "/opus-rail disable" (or off) pauses every rails injection for this session;
  "/opus-rail enable" (or on) resumes; "/opus-rail status" reports hook
  telemetry and mode. Use when the user runs /opus-rail with one of those
  arguments. This is NOT the distribution session-mode skill — on machines
  with the full hook system installed, this control skill is the only
  opus-rail skill that should exist.
---

# opus-rail (full-system session control)

The opus-rails hook watches UserPromptSubmit for the exact prompts
`/opus-rail disable|off|enable|on` and toggles a session-keyed marker BEFORE
this skill loads — so by the time you read this, the toggle has usually
already happened. Your job is to confirm it, not to perform it.

## `/opus-rail disable` (or `off`)

- Look for the hook's confirmation in this turn's context: a line starting
  `OPUS RAILS: paused for this session`.
- If present: tell the user in one line that opus-rail is paused for this
  session, and stand down all opus-rail routing behavior (no forced
  dispatching, no planner-lane requirement) until re-enabled.
- If absent: the hook did not fire — say so plainly (likely the hook isn't
  installed or the settings entry is missing), and apply a behavioral
  stand-down anyway so the user gets what they asked for.
- Then put the seat back on Opus 5: you cannot switch the main model
  yourself, so tell the user to type `/model claude-opus-5` — the id typed
  inline as the argument. Warn them NOT to open the bare `/model` picker:
  it only lists model families, and the env pin keeps the `opus` alias on
  4.8, so the inline full id is the only route to Opus 5. Disabling means
  driving Opus 5 directly; don't leave them on the 4.8 orchestrator.

## `/opus-rail enable` (or `on`, `resume`)

- Look for `OPUS RAILS: resumed` in this turn's context and confirm in one
  line. Rails re-inject from the next prompt; resume opus-rail routing
  behavior immediately.
- If the confirmation is absent, say the hook did not fire and resume the
  routing behavior anyway.
- Then restore the orchestrator seat: tell the user to run `/model opus`
  (the pinned alias → Opus 4.8) if the session is currently on another
  model.

## `/opus-rail status`

Run these read-only checks and report in 2–3 lines, no more:

```bash
echo '{}' | python3 ~/.claude/hooks/opus-rails.py stats
printenv OPUS_RAIL_PLUS
```

Report: injection/observation counts, whether plus mode is set
(`OPUS_RAIL_PLUS=1` → planner drafts ALL plan-shaped work; unset → substantive
plans only), and whether this session is currently paused (the hook printed a
"paused" confirmation more recently than a "resumed" one in this session).

## `/opus-rail` with no argument

One-line reminder: the full system is hook-enforced and always on in opus
sessions — available arguments are `disable`, `enable`, `status`. Do not
switch into any session mode; that is the separate distribution skill.
