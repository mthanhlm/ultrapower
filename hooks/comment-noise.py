#!/usr/bin/env python3
"""PostToolUse hook: reject narration comments in code the agent just wrote.

Keeps only short non-obvious why-notes; bans step markers, restated code, and change logs.
Exit 2 sends the offending lines back so they are cleaned up immediately. Fail-open otherwise.
"""
import json
import os
import re
import sys

PATH_KEYS = ("file_path", "notebook_path", "relative_path")
TEXT_KEYS = ("new_string", "content", "body")

CODE_EXTS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".py", ".go", ".java", ".kt", ".rb", ".rs",
    ".c", ".h", ".cpp", ".hpp", ".cs", ".swift", ".php", ".scala", ".sh", ".bash", ".sql",
    ".vue", ".svelte",
}

ALLOWED = re.compile(
    r"(TODO|FIXME|HACK|NOTE|SAFETY|PERF|WHY)\b|\blean:|noqa|type:\s*ignore|eslint-|ts-ignore|"
    r"ts-expect-error|prettier-|pylint|pragma|coding[:=]|^!",
    re.I,
)

NARRATION = [
    re.compile(r"^(step\s*\d|first,?\s|now\s|next,?\s|then\s|finally,?\s)", re.I),
    re.compile(
        r"^(loop(s|ing)?\s(through|over)|iterat|call(s|ing)?\s(the|a)\b|set(s|ting)?\sthe\b|"
        r"get(s|ting)?\sthe\b|return(s|ing)?\s(the|a)\b|initializ|instantiat|create(s)?\s(a|the|new)\b|"
        r"define(s)?\s(a|the)\b|add(s|ing)?\s(a|the)\b|update(s|ing)?\sthe\b|"
        r"check(s|ing)?\s(if|whether|the)\b|increment|declare)",
        re.I,
    ),
    re.compile(r"^(added|updated|changed|removed|deleted|fixed|modified|refactored|renamed|moved|new[:\s])\b", re.I),
    re.compile(r"^this\s(function|method|class|file|line|block|loop|variable)\b", re.I),
    re.compile(r"^(here\swe\b|we\s(now|then|first|just)\b)", re.I),
]

COMMENT_LINE = re.compile(r"^\s*(//+|#+|\*+|/\*+|--)\s*(.*)$")


def noisy_lines(text):
    hits = []
    for line in text.splitlines():
        m = COMMENT_LINE.match(line)
        if not m:
            continue
        body = m.group(2).strip()
        if not body or ALLOWED.search(line):
            continue
        if any(p.match(body) for p in NARRATION):
            hits.append(line.strip())
    return hits


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    raw = next((tool_input[k] for k in PATH_KEYS if tool_input.get(k)), None)
    if not raw or os.path.splitext(raw)[1].lower() not in CODE_EXTS:
        return 0
    added = "\n".join(tool_input[k] for k in TEXT_KEYS if isinstance(tool_input.get(k), str))
    hits = noisy_lines(added)
    if not hits:
        return 0
    print(
        "Narration comments detected (banned — keep only short non-obvious why-notes):\n  "
        + "\n  ".join(hits[:10]),
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
