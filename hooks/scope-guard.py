#!/usr/bin/env python3
"""PreToolUse hook: deny edits to files outside the locked story contract.

No active story (`.scrum/current-story.json`) -> allow everything, so ad-hoc work and
work in projects that don't use ultrapower are unaffected. Fail-open on any error.
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
    if not story:
        return
    tool_input = data.get("tool_input") or {}
    raw = next((tool_input[k] for k in PATH_KEYS if tool_input.get(k)), None)
    if not raw:
        return
    target = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(cwd, raw))
    if target.startswith(scrum_state.scrum_dir(root) + os.sep):
        return
    if target in set(story.get("files", [])):
        return
    _deny(
        f"{os.path.basename(target)} is outside the contract for story "
        f"'{story.get('id', '?')}'. Stop and tell the user why it is needed; only after their OK "
        f"add it: python3 \"$CLAUDE_PLUGIN_ROOT\"/scripts/scrum_state.py add-file --file <path>"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
