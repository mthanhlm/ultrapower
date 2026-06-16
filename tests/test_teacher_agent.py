import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "teacher.md")

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    text = open(path).read()
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body


def test_file_exists():
    assert os.path.isfile(AGENT), f"agents/teacher.md not found at {AGENT}"


def test_frontmatter_name():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "teacher"


def test_frontmatter_description_nonempty():
    fm, _ = _parse(AGENT)
    assert isinstance(fm.get("description"), str) and fm["description"].strip()


def test_frontmatter_model_opus():
    fm, _ = _parse(AGENT)
    assert fm["model"] == "opus"


def test_frontmatter_read_only():
    fm, _ = _parse(AGENT)
    tools = [t.strip() for t in fm["tools"].split(",")]
    for forbidden in WRITE_TOOLS:
        assert forbidden not in tools, f"tools must not include {forbidden}"


def test_body_three_levels():
    _, body = _parse(AGENT)
    for level in ("Problem", "Solution", "Impact"):
        assert re.search(rf"(?m)^#+\s+{level}\b|^\*\*{level}\b", body, re.IGNORECASE), (
            f"teaching level '{level}' heading missing"
        )


def test_body_teaching_beats():
    _, body = _parse(AGENT)
    low = body.lower()
    for beat in ("restate", "eli5", "eli14", "intern", "askuserquestion", "master", "why"):
        assert beat in low, f"teaching beat '{beat}' missing from body"


def test_body_output_checklist():
    _, body = _parse(AGENT)
    assert "CHECKLIST" in body
    assert "source-tag" in body
