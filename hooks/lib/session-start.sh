#!/usr/bin/env bash
# SessionStart: ensure the CodeGraph index exists, keep .codegraph gitignored,
# and inject a compact project-memory summary. Always exits 0; degrades to
# Grep/Read when CodeGraph is unavailable.
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$LIB/common.sh"

INPUT="$(cat)"
CWD="$(printf '%s' "$INPUT" | json_field cwd)"
PROJ="$(up_project_dir "$CWD")"
mkdir -p "$PROJ/.ultrapower" 2>/dev/null

CTX=""
if up_enabled && up_has_codegraph; then
  ST="$(cd "$PROJ" 2>/dev/null && codegraph status -j 2>/dev/null)"
  INIT="$(printf '%s' "$ST" | json_field initialized)"
  if [ "$INIT" = "true" ]; then
    CTX="CodeGraph index ready."
  else
    if (cd "$PROJ" 2>/dev/null && codegraph init >"$PROJ/.ultrapower/codegraph-init.log" 2>&1); then
      CTX="CodeGraph index initialized for this repo."
    else
      CTX="CodeGraph init attempted (see .ultrapower/codegraph-init.log); structural queries may fall back to Grep/Read."
    fi
  fi
  up_ensure_gitignore "$PROJ"
elif up_enabled; then
  CTX="CodeGraph CLI not found — structural queries fall back to Grep/Read."
else
  CTX="CodeGraph lifecycle disabled (ULTRAPOWER_CODEGRAPH=off)."
fi

MEM="$(python3 "$LIB/memory_summary.py" summary "$PROJ" 2>/dev/null)"
if [ -n "$MEM" ]; then
  CTX="$CTX
$MEM"
else
  CTX="$CTX
No .ultrapower project memory yet. Run /ultrapower:codegraph to capture how this codebase works and its architecture invariants."
fi

UP_CTX="$CTX" python3 - <<'PY'
import os, json
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": os.environ.get("UP_CTX", "")
}}))
PY
exit 0
