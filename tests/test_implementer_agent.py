import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENT = os.path.join(ROOT, "agents", "implementer.md")


def _parse(path):
    assert os.path.isfile(path), f"agent file not found: {path}"
    text = open(path).read()
    parts = text.split("---", 2)
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body


def test_file_exists():
    assert os.path.isfile(AGENT), f"agents/implementer.md not found at {AGENT}"


def test_frontmatter_name():
    fm, _ = _parse(AGENT)
    assert fm["name"] == "implementer"


def test_frontmatter_model_sonnet():
    fm, _ = _parse(AGENT)
    assert fm["model"] == "sonnet"


def test_body_references_lean_ladder():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "ladder" in low, "implementer must reference the lean ladder"
    assert "lean:" in body, "implementer must require the lean: marker convention"


def test_body_states_carve_outs():
    _, body = _parse(AGENT)
    low = body.lower()
    for carve in ("validation", "security", "accessibility"):
        assert carve in low, f"carve-out '{carve}' missing — lazy must not mean negligent"


def test_body_one_runnable_check_reinforces_tdd():
    _, body = _parse(AGENT)
    low = body.lower()
    assert "one runnable check" in low or "one-runnable-check" in low
