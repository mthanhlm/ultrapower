#!/usr/bin/env bash
# Shared helpers for ultrapower hooks.
# IMPORTANT: never use `set -e` here — a hook must never abort the user's session.

up_enabled()       { [ "${ULTRAPOWER_CODEGRAPH:-on}" != "off" ]; }
up_has_codegraph() { command -v codegraph >/dev/null 2>&1; }

# Resolve the project directory: prefer the env Claude Code exports, then the
# hook's reported cwd, then the process cwd.
up_project_dir() {
  local d="${CLAUDE_PROJECT_DIR:-}"
  [ -z "$d" ] && d="${1:-}"
  [ -z "$d" ] && d="$(pwd)"
  printf '%s' "$d"
}

up_state_dir() { printf '%s/.ultrapower/state' "${1:-.}"; }

# Idempotently keep .codegraph and ultrapower transient state out of git,
# while leaving .ultrapower/memory/ tracked. No-op outside a git repo.
up_ensure_gitignore() {
  local proj="$1" gi line
  [ -d "$proj/.git" ] || return 0
  gi="$proj/.gitignore"
  for line in ".codegraph/" ".ultrapower/state/" ".ultrapower/gate.toml" ".ultrapower/*.log"; do
    if [ -f "$gi" ] && grep -qxF "$line" "$gi" 2>/dev/null; then continue; fi
    printf '%s\n' "$line" >> "$gi" 2>/dev/null
  done
}

# Extract a (optionally dot-nested) field from JSON on stdin. Prints the value
# (strings raw, other types as JSON) or nothing if absent.
# NOTE: must use `python3 -c` (not a heredoc): a heredoc would occupy stdin and
# the piped JSON would never reach json.load.
json_field() {
  python3 -c '
import sys, json
keys = sys.argv[1].split(".")
try:
    cur = json.load(sys.stdin)
except Exception:
    sys.exit(0)
for k in keys:
    if isinstance(cur, dict) and k in cur:
        cur = cur[k]
    else:
        sys.exit(0)
if cur is None:
    sys.exit(0)
print(cur if isinstance(cur, str) else json.dumps(cur))
' "$1" 2>/dev/null
}
