# Add to your statusline command script. The statusline receives the session's
# current model id on every render; writing it to these flag files is what lets
# opus-rails.py resolve the model on a session's FIRST prompt and immediately
# after a /model switch. `$input` is the JSON Claude Code pipes to the statusline.
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
sid=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('session_id',''))" 2>/dev/null)
id=$(printf '%s' "$input" | python3 -c "import json,sys;print(json.load(sys.stdin).get('model',{}).get('id',''))" 2>/dev/null)
key=$(printf '%s' "$PWD" | python3 -c "import hashlib,sys;print(hashlib.sha1(sys.stdin.read().encode()).hexdigest()[:16])" 2>/dev/null)
mkdir -p "$cfg/.model-live" 2>/dev/null
[ -n "$sid" ] && printf '%s' "$id" > "$cfg/.model-live/sess-$sid" 2>/dev/null
[ -n "$key" ] && printf '%s' "$id" > "$cfg/.model-live/$key" 2>/dev/null
