import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS = os.path.join(ROOT, "commands", "status.md")


def _parse(path):
    assert os.path.isfile(path), f"command file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_status_exists_and_frontmatter():
    fm, _ = _parse(STATUS)
    assert fm["description"].strip()


def test_status_default_is_read_only_view():
    _, body = _parse(STATUS)
    assert "scrum_state.py" in body and "status" in body
    assert "read-only" in body.lower()


def test_status_surfaces_every_recovery_hatch():
    _, body = _parse(STATUS)
    low = body.lower()
    for hatch in ("abort", "split", "add-file", "red", "done"):
        assert hatch in low, f"recovery hatch '{hatch}' missing from status command"


def test_status_done_override_requires_reason():
    _, body = _parse(STATUS)
    low = body.lower()
    assert "override" in low and "reason" in low


def test_status_abort_releases_lock():
    _, body = _parse(STATUS)
    assert "abort" in body and "blocked" in body.lower()
