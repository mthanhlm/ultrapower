import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "debate.md")

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
LENSES = ["natural", "logical", "user-friendly", "data-flow", "flow"]


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    text = open(path).read()
    parts = text.split("---", 2)
    # parts[0] is empty string before first ---, parts[1] is frontmatter, parts[2] is body
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body


def test_file_exists():
    assert os.path.isfile(AGENT), f"agents/debate.md not found at {AGENT}"


def test_frontmatter_name():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "debate"


def test_frontmatter_description_nonempty():
    fm, _ = _parse(AGENT)
    assert isinstance(fm.get("description"), str) and fm["description"].strip()


def test_frontmatter_model_opus():
    fm, _ = _parse(AGENT)
    assert fm["model"] == "opus"


def test_frontmatter_tools_no_write_tools():
    fm, _ = _parse(AGENT)
    tools_raw = fm["tools"]
    tools = [t.strip() for t in tools_raw.split(",")]
    for forbidden in WRITE_TOOLS:
        assert forbidden not in tools, f"tools must not include {forbidden}"


def test_frontmatter_tools_no_bash():
    fm, _ = _parse(AGENT)
    tools = [t.strip() for t in fm["tools"].split(",")]
    assert "Bash" not in tools, "debate reviews a plan only — Bash must not be in tools"


def test_body_all_five_lenses():
    _, body = _parse(AGENT)
    # Each lens must appear as a distinct heading/label (## or **) to avoid substring false matches.
    # "flow" alone must not match only inside "data-flow"; require a heading boundary.
    patterns = {
        "natural":       r"(?m)^#+\s+Natural\b|^\*\*Natural\b",
        "logical":       r"(?m)^#+\s+Logical\b|^\*\*Logical\b",
        "user-friendly": r"(?m)^#+\s+User-friendly\b|^\*\*User-friendly\b",
        "data-flow":     r"(?m)^#+\s+Data-flow\b|^\*\*Data-flow\b",
        "flow":          r"(?m)^#+\s+Flow\b|^\*\*Flow\b",
    }
    for lens, pat in patterns.items():
        assert re.search(pat, body, re.IGNORECASE), f"lens '{lens}' heading not found in body"


def test_body_severity_vocab():
    _, body = _parse(AGENT)
    for word in ("blocker", "should", "nit"):
        assert word in body, f"severity word '{word}' missing from body"


def test_body_output_block():
    _, body = _parse(AGENT)
    assert "VERDICT" in body
    assert "FINDINGS" in body


def test_body_reviews_plan_not_diff():
    _, body = _parse(AGENT)
    assert "the plan, not the diff" in body
