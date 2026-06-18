#!/usr/bin/env python3
"""PreToolUse hook: stop Bash from writing SOURCE around the edit guards.

scope/tdd/plan guards only see Edit/Write/NotebookEdit. Without this, an agent could write
arbitrary source via shell redirection (`echo > f`, `cat <<EOF > f`, `sed -i`, `tee`, `cp/mv`,
`dd of=`) and bypass the whole forced-increment floor. This hook extracts the write-TARGETS from a
Bash command and, for any that is a source file, applies the SAME plan/lock/scope/tdd decision the
edit guards would (via scrum_state.would_block_edit).

Deliberately conservative: it only denies when it can identify a concrete source write-target, and
FAILS OPEN on anything it can't parse — so verify/build/test commands are never blocked. Source
edits should go through Edit/Write so the guards apply; this is the backstop, the prose is the
first line.
"""
import json
import os
import re
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

# Each pattern captures a candidate write-target path from a shell command.
_TARGET_PATTERNS = [
    re.compile(r"(?<![0-9>&])>>?\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s|&;<>()]+))"),  # > file / >> file
    re.compile(r"\btee\b\s+(?:-a\s+)?(?:\"([^\"]+)\"|'([^']+)'|([^\s|&;<>()]+))"),  # tee [-a] file
    re.compile(r"\bdd\b[^\n]*?\bof=(?:\"([^\"]+)\"|'([^']+)'|([^\s|&;]+))"),         # dd of=file
    re.compile(r"\bsed\b\s+(?:-[A-Za-z]*\s+)*-i[A-Za-z]*\b[^|&;]*?\s(?:\"([^\"]+)\"|'([^']+)'|([^\s|&;]+))\s*$"),
    re.compile(r"\b(?:truncate|install)\b[^|&;]*?\s(?:\"([^\"]+)\"|'([^']+)'|([^\s|&;]+))\s*$"),
]

# Indicators that a command writes files but whose target we may not parse — used only to widen
# scrutiny, never to deny on its own (fail-open keeps verify/build safe).
_CP_MV = re.compile(r"\b(?:cp|mv|rsync|install)\b\s+(.+)")


def _targets(command):
    found = []
    for pat in _TARGET_PATTERNS:
        for m in pat.finditer(command):
            tok = next((g for g in m.groups() if g), None)
            tok = tok.strip("\"'") if tok else tok
            if tok and not tok.startswith("/dev/") and "$" not in tok:
                found.append(tok)
    # cp/mv/rsync: the destination is the last bare token of the segment
    for m in _CP_MV.finditer(command):
        parts = [p for p in re.split(r"\s+", m.group(1).strip()) if p and not p.startswith("-")]
        if len(parts) >= 2 and "$" not in parts[-1]:
            found.append(parts[-1].strip("\"'"))
    return found


def _deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or os.getcwd()
    command = (data.get("tool_input") or {}).get("command")
    if not command or not isinstance(command, str):
        return
    root = scrum_state.find_project_root(cwd)
    for tok in _targets(command):
        target = os.path.realpath(tok if os.path.isabs(tok) else os.path.join(cwd, tok))
        if not scrum_state.is_code_file(target) or scrum_state.is_test_file(target):
            continue
        reason = scrum_state.would_block_edit(root, target)
        if reason:
            _deny(
                f"Bash would write source ({os.path.basename(target)}) around the guards: {reason}. "
                f"Write source via the Edit/Write tools (so scope + TDD apply), not shell redirection."
            )
            return


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
