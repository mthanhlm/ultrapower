import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "step-planner.md")

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_file_exists():
    assert os.path.isfile(AGENT)


def test_frontmatter_name_and_model():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "step-planner"
    assert fm["model"] == "opus"


def test_frontmatter_read_only():
    fm, _ = _parse(AGENT)
    tools = [t.strip() for t in fm["tools"].split(",")]
    for forbidden in WRITE_TOOLS:
        assert forbidden not in tools


def test_body_hard_three_point_cap():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "≤3" in body or "<=3" in body or "3 point" in low
    assert "split" in low, "must require splitting oversized steps"


def test_body_oversized_escape():
    _, body = _parse(AGENT)
    assert "oversized" in body.lower()


def test_body_invokes_ladder_yagni_reuse():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "ladder" in low and "yagni" in low and "reuse" in low


def test_body_degrades_without_codegraph():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "unavailable" in low or "fall back" in low


def test_body_output_steps_block():
    _, body = _parse(AGENT)
    assert "STEPS" in body
    for field in ("files:", "acceptance:", "out:"):
        assert field in body, f"per-step field '{field}' missing"
