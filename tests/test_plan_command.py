import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAN = os.path.join(ROOT, "commands", "plan.md")
INIT = os.path.join(ROOT, "commands", "init.md")


def _parse(path):
    assert os.path.isfile(path), f"command file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_plan_exists_and_frontmatter():
    fm, _ = _parse(PLAN)
    assert fm["description"].strip()
    assert "Agent" in fm["allowed-tools"]


def test_plan_invokes_step_planner():
    _, body = _parse(PLAN)
    assert "step-planner" in body


def test_plan_single_pass_by_default_deep_is_offered():
    _, body = _parse(PLAN)
    low = body.lower()
    assert "single pass" in low
    # deep panel is offered, not silently spent
    assert "offer" in low and "deep" in low


def test_plan_writes_via_state_cli_not_handedit():
    _, body = _parse(PLAN)
    assert "plan-new" in body and "plan-add" in body


def test_plan_refuses_to_clobber_inflight_plan():
    _, body = _parse(PLAN)
    assert "plan-next" in body


def test_init_folds_doctor_and_migration():
    _, body = _parse(INIT)
    low = body.lower()
    assert "doctor" in low
    assert "migrat" in low
    # no visibility prompt anymore
    assert "always local" in low or "always local (gitignored)" in low


def test_init_offers_glossary_seed():
    fm, body = _parse(INIT)
    low = body.lower()
    assert "context.md" in low and "glossary" in low
    # opt-in draft-from-code + interview-when-unclear, skippable for an empty repo
    assert "offer" in low or "optional" in low
    assert "one question at a time" in low or "interview" in low
    assert "skip" in low  # empty/throwaway repo is skipped, not force-seeded
    assert "AskUserQuestion" in fm["allowed-tools"]
