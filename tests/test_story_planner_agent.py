import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "story-planner.md")

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    text = open(path).read()
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body


def test_file_exists():
    assert os.path.isfile(AGENT), f"agents/story-planner.md not found at {AGENT}"


def test_frontmatter_name_and_model():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "story-planner"
    assert fm["model"] == "opus"


def test_frontmatter_read_only():
    fm, _ = _parse(AGENT)
    tools = [t.strip() for t in fm["tools"].split(",")]
    for forbidden in WRITE_TOOLS:
        assert forbidden not in tools, f"tools must not include {forbidden}"


def test_body_invokes_ladder_yagni():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "ladder" in low
    assert "yagni" in low
    assert "laziest" in low


def test_body_rejects_speculative_files():
    _, body = _parse(AGENT)
    assert "speculative" in body.lower()


def test_body_brief_block_unchanged():
    _, body = _parse(AGENT)
    assert "BRIEF" in body
    for field in ("What:", "You'll receive:", "Files touched:", "Affected sites:",
                  "Out of scope:", "Verify:", "Estimate:"):
        assert field in body, f"BRIEF field '{field}' missing"
