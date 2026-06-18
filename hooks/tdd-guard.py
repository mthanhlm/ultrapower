#!/usr/bin/env python3
"""PreToolUse hook: enforce test-first inside a locked step.

While a step is active and no failing test has yet been observed, deny edits to its non-test
contract files. Test files stay editable so the test can be written first. The implementer
clears the gate with `scrum_state.py mark-red` after seeing red. The per-CRITERION close gate
(`check-tdd`) is what keeps a multi-criterion step from going green on a single red test; this
hook only enforces "a failing test exists before any source edit". Fail-open.
"""
import json
import os
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

PATH_KEYS = ("file_path", "notebook_path", "relative_path")


def _deny(reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or os.getcwd()
    root = scrum_state.find_project_root(cwd)
    story = scrum_state.load_current_story(root)
    if not story or story.get("kind") == "refactor" or scrum_state.red_unlocked(story):
        return
    tool_input = data.get("tool_input") or {}
    raw = next((tool_input[k] for k in PATH_KEYS if tool_input.get(k)), None)
    if not raw:
        return
    target = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(cwd, raw))
    if target not in set(story.get("files", [])) or scrum_state.is_test_file(target):
        return
    _deny(
        f"TDD: write a failing test for step '{story.get('id', '?')}' first. Edit the test, run "
        f"it, watch it fail, then run: python3 \"$CLAUDE_PLUGIN_ROOT\"/scripts/scrum_state.py "
        f"mark-red — source edits unlock after that."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
