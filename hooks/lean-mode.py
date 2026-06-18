#!/usr/bin/env python3
"""UserPromptSubmit hook: track /up:lean switches and persist the project's lean intensity.

Recognises `/up:lean <lite|full|ultra|off>` and "stop lean"/"normal mode", writes lean_mode to
.scrum/config.json, and re-emits the ladder at the new level so the switch takes effect at once.
Silent on every other prompt. Always-on (no active story required) so the toggle works anywhere.
Fail-open.
"""
import json
import os
import re
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

_SWITCH = re.compile(r"^/?up:lean\b(?:\s+(\S+))?", re.I)
_OFF = re.compile(r"^\s*(stop lean|normal mode)\s*\.?\s*$", re.I)


def _wanted_mode(prompt):
    if _OFF.search(prompt):
        return "off"
    m = _SWITCH.match(prompt)
    if m:
        return scrum_state._normalize_lean_mode(m.group(1)) or scrum_state.DEFAULT_LEAN_MODE
    return None


def main():
    data = json.load(sys.stdin)
    prompt = (data.get("prompt") or "").strip()
    mode = _wanted_mode(prompt)
    if not mode:
        return
    root = scrum_state.find_project_root(data.get("cwd") or os.getcwd())
    if not os.path.isdir(scrum_state.scrum_dir(root)):
        return
    cfg = scrum_state.load_config(root)
    cfg["lean_mode"] = mode
    scrum_state.save_config(root, cfg)
    ladder = scrum_state.ladder_text(mode)
    context = f"LEAN MODE → {mode}" + (f"\n\n{ladder}" if ladder else " (lean disabled)")
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": context,
    }}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(0)
