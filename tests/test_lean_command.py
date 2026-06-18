import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMD = os.path.join(ROOT, "commands", "lean.md")


def _body():
    assert os.path.isfile(CMD), f"commands/lean.md not found at {CMD}"
    return open(CMD).read()


def test_file_exists():
    assert os.path.isfile(CMD)


def test_documents_four_levels():
    low = _body().lower()
    for level in ("lite", "full", "ultra", "off"):
        assert level in low, f"level '{level}' missing from /up:lean docs"


def test_persists_lean_mode():
    body = _body()
    assert "lean_mode" in body
    assert ".scrum/config.json" in body


def test_references_ladder():
    assert "ladder" in _body().lower()


def test_credits_ponytail():
    assert "ponytail" in _body().lower()
