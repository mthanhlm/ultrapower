#!/usr/bin/env python3
"""Print the proposed new content from a Write/Edit/MultiEdit hook payload.

Reads the full hook JSON on stdin, emits the concatenated new text so the
invariant backstop can grep it for forbidden imports. Fail-open: prints nothing
on any problem.
"""
import sys, json

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

ti = d.get("tool_input", {}) if isinstance(d, dict) else {}
parts = []
if isinstance(ti, dict):
    if isinstance(ti.get("content"), str):
        parts.append(ti["content"])
    if isinstance(ti.get("new_string"), str):
        parts.append(ti["new_string"])
    eds = ti.get("edits")
    if isinstance(eds, list):
        for e in eds:
            if isinstance(e, dict):
                for key in ("new_string", "new_text"):
                    if isinstance(e.get(key), str):
                        parts.append(e[key])

print("\n".join(parts))
