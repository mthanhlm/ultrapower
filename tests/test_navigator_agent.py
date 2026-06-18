import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "navigator.md")

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    text = open(path).read()
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body


def test_file_exists():
    assert os.path.isfile(AGENT), f"agents/navigator.md not found at {AGENT}"


def test_frontmatter_name():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "navigator"


def test_frontmatter_description_nonempty():
    fm, _ = _parse(AGENT)
    assert isinstance(fm.get("description"), str) and fm["description"].strip()


def test_frontmatter_description_lens_count():
    fm, _ = _parse(AGENT)
    desc = fm["description"].lower()
    assert "six" in desc and "five" not in desc, "description lens count must match the six-lens body"


def test_frontmatter_model_opus():
    fm, _ = _parse(AGENT)
    assert fm["model"] == "opus"


def test_frontmatter_tools_no_write_tools():
    fm, _ = _parse(AGENT)
    tools_raw = fm["tools"]
    tools = [t.strip() for t in tools_raw.split(",")]
    for forbidden in WRITE_TOOLS:
        assert forbidden not in tools, f"tools must not include {forbidden}"


def test_body_all_six_lenses():
    _, body = _parse(AGENT)
    # Each lens must appear as a distinct heading to avoid substring false matches.
    # "flow" alone must not match only inside "data-flow"; require a heading boundary.
    patterns = {
        "natural":       r"(?m)^#+\s+Natural\b|^\*\*Natural\b",
        "logical":       r"(?m)^#+\s+Logical\b|^\*\*Logical\b",
        "user-friendly": r"(?m)^#+\s+User-friendly\b|^\*\*User-friendly\b",
        "data-flow":     r"(?m)^#+\s+Data-flow\b|^\*\*Data-flow\b",
        "flow":          r"(?m)^#+\s+Flow\b|^\*\*Flow\b",
        "lean":          r"(?m)^#+\s+Lean\b|^\*\*Lean\b",
    }
    for lens, pat in patterns.items():
        assert re.search(pat, body, re.IGNORECASE), f"lens '{lens}' heading not found in body"


def test_body_lean_lens_tags_and_net():
    _, body = _parse(AGENT)
    low = body.lower()
    for tag in ("delete", "stdlib", "native", "yagni", "shrink"):
        assert tag in low, f"lean-lens tag '{tag}' missing from body"
    assert "net:" in low, "lean lens must close with a net: -N lines metric"


def test_body_severity_vocab():
    _, body = _parse(AGENT)
    for word in ("blocker", "should", "nit"):
        assert word in body, f"severity word '{word}' missing from body"


def test_body_output_block():
    _, body = _parse(AGENT)
    assert "VERDICT" in body
    assert "FINDINGS" in body
