import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "diagnostician.md")


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_file_exists():
    assert os.path.isfile(AGENT)


def test_frontmatter_name_and_model():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "diagnostician"
    assert fm["model"] == "opus"


def test_body_red_capable_loop_before_hypothesis():
    _, body = _parse(AGENT)
    flat = " ".join(body.lower().split())  # collapse wrapping so phrase matches across line breaks
    assert "red-capable" in flat
    # the discipline: build the loop before forming any hypothesis
    assert "before any hypothesis" in flat or "before forming any hypothesis" in flat


def test_body_ranked_falsifiable_hypotheses():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "falsifiable" in low
    assert "3" in body and "hypothes" in low


def test_body_does_not_ship_the_fix():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "do not ship" in low or "not ship" in low or "never ship" in low


def test_body_output_block():
    _, body = _parse(AGENT)
    for field in ("ROOT CAUSE", "REGRESSION TEST", "LOOP"):
        assert field in body
