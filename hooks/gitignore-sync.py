#!/usr/bin/env python3
"""SessionStart hook: sync .gitignore managed entries for ultrapower projects."""
import json
import os
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402


def main():
    data = json.load(sys.stdin)
    root = scrum_state.find_project_root(data.get("cwd") or os.getcwd())
    if not os.path.isfile(scrum_state.config_path(root)):
        return
    scrum_state.sync_gitignore(root)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
