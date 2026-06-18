import os

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = os.path.join(ROOT, "commands", "run.md")


def _parse(path):
    assert os.path.isfile(path), f"command file not found: {path}"
    parts = open(path).read().split("---", 2)
    return yaml.safe_load(parts[1]), parts[2]


def test_run_exists_and_frontmatter():
    fm, _ = _parse(RUN)
    assert fm["description"].strip()
    assert "Agent" in fm["allowed-tools"]


def test_run_full_cycle_present_and_ordered():
    _, body = _parse(RUN)
    # read-contract -> lock -> implement -> review -> check-tdd -> done-gate -> close, in order.
    order = ["plan-step --id", "lock --id", "`implementer`", "`navigator`", "check-tdd",
             "done-gate.py", "lean-debt"]
    positions = [body.find(tok) for tok in order]
    assert all(p != -1 for p in positions), dict(zip(order, positions))
    assert positions == sorted(positions), "cycle steps are out of order"


def test_run_review_and_gate_precede_close_bookkeeping():
    _, body = _parse(RUN)
    # close bookkeeping (lean-debt) comes after both the review and the gate
    assert body.find("`navigator`") < body.find("lean-debt")
    assert body.find("done-gate.py") < body.find("lean-debt")


def test_run_sources_contract_and_forbids_shell_writes():
    _, body = _parse(RUN)
    assert "plan-step" in body, "run must read the contract from plan-step, not fabricate args"
    low = body.lower()
    assert "shell redirection" in low or "never shell" in low
    assert "points` are `> 3" in body or "points > 3" in body or "> 3" in body


def test_run_invokes_implementer_agent():
    _, body = _parse(RUN)
    assert "implementer" in body and "opus" in body.lower()


def test_run_panel_review_for_risky_steps():
    _, body = _parse(RUN)
    low = body.lower()
    assert "panel" in low and ("≥2" in body or ">=2" in body or "2 agree" in low)


def test_run_pauses_at_boundaries():
    _, body = _parse(RUN)
    low = body.lower()
    assert "boundar" in low
    for boundary in ("oversized", "blocker", "red gate", "complet"):
        assert boundary in low, f"boundary '{boundary}' not documented"


def test_run_never_commits():
    _, body = _parse(RUN)
    assert "never commit" in body.lower()


def test_run_supports_all_and_single_step():
    _, body = _parse(RUN)
    assert "all" in body and "<step-id>" in body
