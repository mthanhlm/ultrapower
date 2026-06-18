#!/usr/bin/env python3
"""SessionStart hook: inject the lean ladder into every ultrapower session.

Silent when the ladder is unreadable or the project has no .scrum/ (so non-ultrapower
repos are untouched). Fail-open.
"""
import json
import os
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402


def main():
    data = json.load(sys.stdin)
    root = scrum_state.find_project_root(data.get("cwd") or os.getcwd())
    if not os.path.isdir(scrum_state.scrum_dir(root)):
        return
    text = scrum_state.ladder_text()
    if not text:
        return
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": text,
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
