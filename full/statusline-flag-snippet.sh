# Add to your statusline command script (settings.json -> statusLine.command).
# Claude Code pipes a JSON payload to the statusline on stdin each render; it
# includes the session's current model id. Writing it to a session-keyed flag is
# what lets opus-rails.py resolve the model on a session's FIRST prompt and
# immediately after a /model switch. (Session-keyed only — a cwd-keyed flag was
# removed after it cross-contaminated concurrent sessions in the same directory.)
input=$(cat)   # capture the stdin payload ONCE, at the top of your script
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
sid=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
id=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('model',{}).get('id',''))" 2>/dev/null)
mkdir -p "$cfg/.model-live" 2>/dev/null
# Guard both: never truncate a good flag with an empty id on a partial render.
[ -n "$sid" ] && [ -n "$id" ] && printf '%s' "$id" > "$cfg/.model-live/sess-$sid" 2>/dev/null
