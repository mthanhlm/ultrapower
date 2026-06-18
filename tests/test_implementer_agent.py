import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "implementer.md")


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_file_exists():
    assert os.path.isfile(AGENT)


def test_frontmatter_name():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "implementer"


def test_frontmatter_model_opus_high_effort():
    fm, _ = _parse(AGENT)
    assert fm["model"] == "opus"
    assert fm["effort"] in {"high", "xhigh", "max"}, "code-writer must reason at high effort"


def test_body_references_lean_ladder_and_marker():
    _, body = _parse(AGENT)
    assert "ladder" in body.lower()
    assert "lean:" in body


def test_body_per_criterion_mark_red():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "mark-red" in body
    assert "--criterion" in body, "must mark each criterion red (per-criterion latch)"
    assert "per criterion" in low or "per-criterion" in low or "each criterion" in low


def test_body_states_carve_outs():
    _, body = _parse(AGENT)
    low = body.lower()
    for carve in ("validation", "security", "accessibility"):
        assert carve in low, f"carve-out '{carve}' missing — lazy must not mean negligent"


def test_body_output_block():
    _, body = _parse(AGENT)
    assert "Done:" in body and "Verify:" in body
