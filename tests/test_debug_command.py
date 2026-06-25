import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG = os.path.join(ROOT, "commands", "debug.md")


def _parse(path):
    assert os.path.isfile(path), f"command file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_debug_exists_and_frontmatter():
    fm, _ = _parse(DEBUG)
    assert fm["description"].strip()
    assert "Agent" in fm["allowed-tools"]


def test_debug_invokes_diagnostician():
    _, body = _parse(DEBUG)
    assert "diagnostician" in body


def test_debug_gates_on_red_capable_repro():
    _, body = _parse(DEBUG)
    low = body.lower()
    assert "red-capable" in low
    # the hard gate: no proven repro -> no fix
    assert "no loop" in low or "no proof" in low or "hard gate" in low


def test_debug_drives_fix_through_locked_flow():
    _, body = _parse(DEBUG)
    # the fix goes through the normal plan/run flow, not a hand-patch in the command
    assert "/up:plan" in body
