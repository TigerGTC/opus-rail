# Full system install

Requires: Claude Code ≥ 2.1.219 (the `opus` alias resolves to Opus 5 from there; the
env pin below is what re-points it at 4.8).

1. **Hook**:
   ```bash
   mkdir -p ~/.claude/hooks && cp hooks/opus-rails.py ~/.claude/hooks/ && chmod +x ~/.claude/hooks/opus-rails.py
   ```

2. **Agents**:
   ```bash
   mkdir -p ~/.claude/agents && cp agents/*.md ~/.claude/agents/
   ```

3. **Settings**: merge `settings-snippet.json` into `~/.claude/settings.json` —
   the `env` block pins the `opus` alias to Opus 4.8, and the `hooks` entries wire
   the five hook events. **Note the pin is machine-wide**: every project and every
   `--model opus` / `/model opus` on this machine resolves to 4.8 afterward; only a
   full id (`/model claude-opus-5`) bypasses it. If `~/.claude/settings.json` doesn't exist or has no
   `env`/`hooks` keys, you can paste the snippet's blocks in wholesale; if you
   already have hooks on those events, append the opus-rails command objects to
   your existing arrays — don't replace them.

4. **Plus mode (optional)**: by default the `planner` lane drafts substantive
   plans and designs; add `"OPUS_RAIL_PLUS": "1"` to the same `env` block to have
   it draft ALL plan-shaped work, however small. The `redteam` lane is on-demand
   in both modes — just ask the orchestrator to redteam something.

5. **Statusline flag (recommended)**: the hook decides "is this session Opus?" from a
   flag your statusline writes each render (freshest source right after a `/model`
   switch, and the only source on a session's first prompt). The statusline is the
   command configured under `statusLine.command` in `~/.claude/settings.json`; Claude
   Code pipes it a JSON payload on stdin each render. Add the lines in
   `statusline-flag-snippet.sh` to that script (it shows how to capture the stdin
   payload). Without this, everything still works from each session's second
   exchange onward via transcript scan.

6. Verify:
   - `claude --model opus --print "Reply with only your exact model id"` → `claude-opus-4-8`
   - In an interactive opus session, the first prompt shows the OPUS RAILS block; an
     implementation-shaped prompt adds a ROUTING CHECK.
   - After some work: `echo '{}' | python3 ~/.claude/hooks/opus-rails.py stats` —
     injections and dispatches are reported separately.

To run raw Opus 5 as the main model anyway: `/model claude-opus-5` (the pin only
affects the alias).

## Uninstall

Remove the env pin and the five opus-rails hook entries from
`~/.claude/settings.json`, then:

```bash
rm ~/.claude/hooks/opus-rails.py ~/.claude/agents/{executor,planner,redteam,worker}.md
rm -rf ~/.claude/.opus-rails ~/.claude/.model-live
```

(`.opus-rails/` holds per-session markers and the telemetry log; `.model-live/`
holds the statusline model flags.)
