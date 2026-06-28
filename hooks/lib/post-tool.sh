#!/usr/bin/env bash
# PostToolUse(Write|Edit|MultiEdit): enqueue the changed path for a debounced
# CodeGraph sync at Stop. No sync per keystroke. Exits 0.
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$LIB/common.sh"

INPUT="$(cat)"
FP="$(printf '%s' "$INPUT" | json_field tool_input.file_path)"
[ -z "$FP" ] && exit 0
CWD="$(printf '%s' "$INPUT" | json_field cwd)"
PROJ="$(up_project_dir "$CWD")"
SID="$(printf '%s' "$INPUT" | json_field session_id)"
[ -z "$SID" ] && SID="default"

SD="$(up_state_dir "$PROJ")"; mkdir -p "$SD" 2>/dev/null
printf '%s\n' "$FP" >> "$SD/$SID.queue" 2>/dev/null
exit 0
