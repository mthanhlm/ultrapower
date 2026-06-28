#!/usr/bin/env bash
# PreToolUse(Write|Edit|MultiEdit): architecture-invariant backstop.
# Denies a block-severity violation, asks on a warn-severity one, otherwise
# allows. Cheap: path globs + import grep against codebase.toml — no codegraph
# call on this hot path. Records touched files for the Stop summary. Exits 0.
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$LIB/common.sh"

INPUT="$(cat)"
FP="$(printf '%s' "$INPUT" | json_field tool_input.file_path)"
[ -z "$FP" ] && exit 0
CWD="$(printf '%s' "$INPUT" | json_field cwd)"
PROJ="$(up_project_dir "$CWD")"

# Best-effort: record the touched file + activity under the session state dir.
SD="$(up_state_dir "$PROJ")"; mkdir -p "$SD" 2>/dev/null
LOG="$SD/activity.log"
SID="$(printf '%s' "$INPUT" | json_field session_id)"
[ -n "$SID" ] && printf '%s\n' "$FP" >> "$SD/$SID.touched" 2>/dev/null

DEC="$(printf '%s' "$INPUT" | python3 "$LIB/extract_content.py" | python3 "$LIB/invariant_check.py" "$PROJ" "$FP" 2>/dev/null)"
D="$(printf '%s' "$DEC" | json_field decision)"
R="$(printf '%s' "$DEC" | json_field reason)"

case "$D" in
  deny)
    printf 'guard deny %s\n' "$FP" >> "$LOG" 2>/dev/null
    UP_R="$R" python3 - <<'PY'
import os, json
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "deny",
    "permissionDecisionReason": "[ultrapower guard] " + os.environ.get("UP_R", "architecture invariant violation")
        + " Reuse the sanctioned layer, or record a deliberate exception as an ADR in .ultrapower/memory/decisions.toml (and add exempt_paths to the invariant)."
}}))
PY
    ;;
  ask)
    printf 'guard ask %s\n' "$FP" >> "$LOG" 2>/dev/null
    UP_R="$R" python3 - <<'PY'
import os, json
print(json.dumps({"hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "permissionDecision": "ask",
    "permissionDecisionReason": "[ultrapower guard] " + os.environ.get("UP_R", "possible architecture concern") + " Confirm this is intended."
}}))
PY
    ;;
  *)
    : ;;
esac
exit 0
