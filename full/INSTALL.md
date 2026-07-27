# Full system install

Requires: Claude Code ≥ 2.1.219 (the `opus` alias resolves to Opus 5 from there; the
env pin below is what re-points it at 4.8).

1. **Hook**: copy `hooks/opus-rails.py` to `~/.claude/hooks/opus-rails.py` and
   `chmod +x` it.

2. **Agents**: copy `agents/executor.md`, `agents/redteam.md`, `agents/worker.md`
   into `~/.claude/agents/`.

3. **Settings**: merge `settings-snippet.json` into `~/.claude/settings.json` —
   the `env` block pins the `opus` alias to Opus 4.8, and the `hooks` entries wire
   the five hook events. If you already have hooks on those events, append the
   opus-rails commands to your existing arrays.

4. **Statusline flag (recommended)**: the hook decides "is this session Opus?" from a
   flag your statusline writes each render (freshest source right after a `/model`
   switch, and the only source on a session's first prompt). Add the lines in
   `statusline-flag-snippet.sh` to your statusline command. Without it, everything
   still works from each session's second exchange onward via transcript scan.

5. Verify:
   - `claude --model opus --print "Reply with only your exact model id"` → `claude-opus-4-8`
   - In an interactive opus session, the first prompt shows the OPUS RAILS block; an
     implementation-shaped prompt adds a ROUTING CHECK.
   - After some work: `echo '{}' | python3 ~/.claude/hooks/opus-rails.py stats` —
     injections and dispatches are reported separately.

To run raw Opus 5 as the main model anyway: `/model claude-opus-5` (the pin only
affects the alias).
