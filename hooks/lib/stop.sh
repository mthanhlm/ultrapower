#!/usr/bin/env bash
# Stop / SubagentStop. When files changed this turn:
#   1. one debounced `codegraph sync -q`
#   2. compute impacted tests (`codegraph affected`) and remind to run them
#   3. edge-check: re-scan changed files ON DISK against block/warn invariants
#      (layer-2 defense for CASE 1 — catches what the live guard missed)
#   4. append an activity-log line; stash a note surfaced on the next prompt
# Always exits 0.
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$LIB/common.sh"

INPUT="$(cat)"
CWD="$(printf '%s' "$INPUT" | json_field cwd)"
PROJ="$(up_project_dir "$CWD")"
SID="$(printf '%s' "$INPUT" | json_field session_id)"
[ -z "$SID" ] && SID="default"

SD="$(up_state_dir "$PROJ")"
Q="$SD/$SID.queue"
LT="$SD/$SID.lastturn"
LOG="$SD/activity.log"

[ -s "$Q" ] || exit 0   # nothing changed this turn

FILES="$(sed '/^$/d' "$Q" | sort -u)"
NCHANGED="$(printf '%s\n' "$FILES" | grep -c . )"
AFFECTED=""

if up_enabled && up_has_codegraph; then
  (cd "$PROJ" 2>/dev/null && codegraph sync -q >/dev/null 2>&1)
  REL="$(printf '%s\n' "$FILES" | while IFS= read -r f; do
           [ -n "$f" ] && python3 -c 'import os,sys;print(os.path.relpath(sys.argv[1],sys.argv[2]))' "$f" "$PROJ" 2>/dev/null
         done)"
  AFFECTED="$(printf '%s\n' "$REL" | (cd "$PROJ" 2>/dev/null && codegraph affected --stdin -q 2>/dev/null) | sed '/^$/d')"
fi

REPORT=""
if [ -n "$AFFECTED" ]; then
  REPORT="Impacted tests for this turn's changes — confirm they ran and are green:
$(printf '%s\n' "$AFFECTED" | sed 's/^/  - /')"
fi

VIOL="$(printf '%s\n' "$FILES" | python3 "$LIB/invariant_check.py" --disk "$PROJ" 2>/dev/null)"
if [ -n "$VIOL" ]; then
  REPORT="${REPORT:+$REPORT
}Architecture guard re-scan flagged code now on disk:
$(printf '%s\n' "$VIOL" | sed 's/^/  - /')"
fi

mkdir -p "$SD" 2>/dev/null
printf 'stop changed=%s affected=%s violations=%s\n' \
  "$NCHANGED" "$(printf '%s' "$AFFECTED" | grep -c . )" "$(printf '%s' "$VIOL" | grep -c . )" \
  >> "$LOG" 2>/dev/null

: > "$Q" 2>/dev/null

if [ -n "$REPORT" ]; then
  printf '%s\n' "$REPORT" > "$LT" 2>/dev/null
  UP_R="$REPORT" python3 -c 'import os,json;print(json.dumps({"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"[ultrapower] "+os.environ.get("UP_R","")}}))'
else
  rm -f "$LT" 2>/dev/null
fi
exit 0
