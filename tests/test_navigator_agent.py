import os
import re

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "navigator.md")

WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_file_exists():
    assert os.path.isfile(AGENT)


def test_frontmatter_name_and_model():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "navigator"
    assert fm["model"] == "opus"


def test_frontmatter_read_only():
    fm, _ = _parse(AGENT)
    tools = [t.strip() for t in fm["tools"].split(",")]
    for forbidden in WRITE_TOOLS:
        assert forbidden not in tools


def test_bug_lenses_always_run():
    _, body = _parse(AGENT)
    # Logical + Flow are the always-on bug-catching floor.
    assert re.search(r"(?im)^#+\s+Logical\b.*always|Logical\b.*\(always\)", body) or "Logical (always)" in body
    assert "Flow (always)" in body


def test_polish_lenses_scale_with_size():
    _, body = _parse(AGENT)
    low = body.lower()
    # depth scales but the floor never gates to zero
    assert "> 2 point" in body or ">2pt" in low or "> 2pt" in body
    assert "natural" in low and "user-friendly" in low and "data-flow" in low


def test_single_reviewer_no_debate_dependency():
    _, body = _parse(AGENT)
    assert "the one review" in body.lower() or "single review" in body.lower()


def test_comments_lens_carries_shared_team_standard():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "shared" in low and "team" in low
    # the lens maps an unmeaningful comment onto the existing tiers
    assert "at least `should`" in low or "at least should" in low
    assert "blocker" in low and "delete-test" in low


def test_closing_lean_check_references_ladder_self_check():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "self-check" in low and "ladder" in low


def test_severity_and_output_block():
    _, body = _parse(AGENT)
    for word in ("blocker", "should", "nit"):
        assert word in body
    assert "VERDICT" in body and "FINDINGS" in body
