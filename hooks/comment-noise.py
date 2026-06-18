#!/usr/bin/env python3
"""PostToolUse hook: reject pure narration comments in code the agent just wrote.

High-PRECISION on purpose: it should only catch comments that restate mechanics and add no
reason, never a legitimate why-note. Three guards against false positives:
  - only single-line `//` and `#` comments are inspected (JSDoc/`*` doc bodies and `--` SQL prose
    are left alone — they were the worst false-positive sources);
  - a comment carrying a rationale connective (because / to avoid / so that / …) is always kept,
    even if it opens with a narration verb ("get the lock first to avoid deadlock");
  - only SHORT comments can be narration — a long sentence is explaining something, not narrating.
Exit 2 sends the offending lines back. Fail-open otherwise.
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

# A rationale connective means the comment is explaining WHY — never narration. Keep it.
# Phrase forms only: bare domain nouns (race/cycle/fallback) are too easily part of pure narration
# ("# update the cycle counter"), so a rationale must be an actual connective.
RATIONALE = re.compile(
    r"\b(because|since|so that|so it|so we|so the|to avoid|to prevent|to ensure|to keep|to stop|"
    r"to handle|to work around|in order to|otherwise|due to|avoids?|prevents?|ensures?|"
    r"workaround|edge case)\b",
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

# Only `//` and `#` line comments — block-comment/JSDoc (`*`, `/*`) and SQL (`--`) prose are exempt.
COMMENT_LINE = re.compile(r"^\s*(//+|#+)\s*(.*)$")

# A genuine narration comment is terse; a longer line is carrying an explanation. The NARRATION
# patterns already require a narration verb/structure at line start, so a slightly higher cap stays
# precise while catching the 7–10 word restated-mechanics lines that 6 let through.
MAX_NARRATION_WORDS = 10


def noisy_lines(text):
    hits = []
    for line in text.splitlines():
        m = COMMENT_LINE.match(line)
        if not m:
            continue
        body = m.group(2).strip()
        if not body or ALLOWED.search(line) or RATIONALE.search(body):
            continue
        if len(body.split()) > MAX_NARRATION_WORDS:
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
    texts = [tool_input[k] for k in TEXT_KEYS if isinstance(tool_input.get(k), str)]
    # MultiEdit carries written text in edits[i]["new_string"], not a top-level key.
    texts += [e["new_string"] for e in (tool_input.get("edits") or [])
              if isinstance(e, dict) and isinstance(e.get("new_string"), str)]
    hits = noisy_lines("\n".join(texts))
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
