#!/usr/bin/env python3
"""PreToolUse hook: keep an unfinished plan from being bypassed by a free-form code dump.

The forcing function of ultrapower is decomposition: a task is broken into small locked steps
and worked one at a time. scope-guard/tdd-guard only arm WHILE a step is locked, so without this
hook an agent could edit arbitrary source between steps and rebuild the very bundle the plugin
exists to prevent. plan-guard closes that gap: when a plan has unfinished steps but no step is
locked, it denies edits to SOURCE files and points at the one-key escape.

Scoped to source files only (by extension, excluding tests) so docs, config, markdown, and
ad-hoc edits in a repo with no plan are never blocked — it is a forcing function, not a trap.
Fail-open on any error.
"""
import json
import os
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

PATH_KEYS = ("file_path", "notebook_path", "relative_path")


def _deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
    }}))


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or os.getcwd()
    root = scrum_state.find_project_root(cwd)
    # A locked step is governed by scope-guard/tdd-guard; no plan means ad-hoc work — both inert here.
    if scrum_state.load_current_story(root) or not scrum_state.has_unfinished_plan(root):
        return
    tool_input = data.get("tool_input") or {}
    raw = next((tool_input[k] for k in PATH_KEYS if tool_input.get(k)), None)
    if not raw:
        return
    target = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(cwd, raw))
    if target.startswith(scrum_state.scrum_dir(root) + os.sep):
        return
    if target != root and not target.startswith(root + os.sep):
        return  # out-of-tree write (e.g. /tmp scratch) is out of scope, not a bypass
    if not scrum_state.is_code_file(target) or scrum_state.is_test_file(target):
        return
    _deny(
        "An unfinished plan exists but no step is locked — edit source through the decomposition, "
        "not around it. Run /up:run to lock and drive the next step, or /up:status abort to clear "
        "the plan. (Docs, config, and non-code files are not blocked.)"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
