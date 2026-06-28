#!/usr/bin/env bash
# UserPromptSubmit:
#   - surface any note the previous turn left (impacted tests to confirm,
#     on-disk invariant findings) — regardless of this prompt's kind;
#   - on a code-intent prompt, inject the Necessity/Reuse ladder, the
#     lean/push-back ethos, blast-radius sizing, the verification bar, and the
#     active architecture invariants.
# Soft (context only) — never blocks. Exits 0.
LIB="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$LIB/common.sh"

INPUT="$(cat)"
PROMPT="$(printf '%s' "$INPUT" | json_field prompt)"
CWD="$(printf '%s' "$INPUT" | json_field cwd)"
PROJ="$(up_project_dir "$CWD")"
SID="$(printf '%s' "$INPUT" | json_field session_id)"

# Carry forward the previous turn's Stop note (consume once).
CARRY=""
if [ -n "$SID" ]; then
  LT="$(up_state_dir "$PROJ")/$SID.lastturn"
  if [ -s "$LT" ]; then
    CARRY="$(cat "$LT" 2>/dev/null)"
    rm -f "$LT" 2>/dev/null
  fi
fi

CTX=""
if printf '%s' "$PROMPT" | grep -qiE '\b(implement|add|fix|refactor|creat|build|chang|updat|writ|renam|delet|remov|migrat|optimi|debug|wire|integrat|introduc|support)\b'; then
  INV="$(python3 "$LIB/memory_summary.py" invariants "$PROJ" 2>/dev/null)"
  [ -z "$INV" ] && INV="(none recorded yet)"
  CTX="[ultrapower] Before editing code, answer the Necessity/Reuse Ladder briefly, in order:
1) Does this need to exist? (no -> skip it; YAGNI)
2) Already in this codebase? (reuse it — search with codegraph; don't rewrite)
3) Stdlib does it?  4) Native platform feature?  5) Installed dependency?  6) One line?  7) Only then: the minimum that works.
Size by BLAST RADIUS (codegraph impact/callers), not line count: trivial -> one pass, no ceremony; wide fan-out -> decompose into visible steps.
Be surgical and lean. If the request looks unreasonable, mis-scoped, wrong-layer, or debt-prone, PUSH BACK and propose the better path BEFORE editing — the user is not always right.
Done means verified: run the impacted tests (codegraph affected --stdin), lint the changed files; compiling/typechecking alone is NOT 'verified'.
Architecture invariants in effect (the guard will block edits that violate a block-severity one):
$INV"
fi

if [ -n "$CARRY" ]; then
  CTX="[ultrapower] Since your last turn:
$CARRY${CTX:+

$CTX}"
fi

[ -z "$CTX" ] && exit 0

UP_CTX="$CTX" python3 -c 'import os,json;print(json.dumps({"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":os.environ.get("UP_CTX","")}}))'
exit 0
