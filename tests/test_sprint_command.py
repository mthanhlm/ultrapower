import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMD = os.path.join(ROOT, "commands", "sprint.md")


def _section(name):
    # the command doc splits into its `## plan` and `## close` halves
    text = open(CMD).read()
    plan, _, close = text.partition("## close")
    return plan if name == "plan" else close


def test_file_exists():
    assert os.path.isfile(CMD)


def test_plan_renumbers_backlog_b_to_s():
    # pulling a backlog item into the sprint renames its B id to an S id
    assert "`B`→`S`" in _section("plan")


def test_close_renumbers_carryback_s_to_b():
    # carrying an unfinished sprint story back to the backlog renames its S id to a B id
    assert "`S`→`B`" in _section("close")


def test_plan_writes_open_worklist_without_timebox():
    # the sprint is an open worklist — no fixed length or start date is written to sprint.md
    plan = _section("plan")
    assert "sprint_length_days" not in plan
    assert "date +%Y-%m-%d" not in plan
    assert "story table" in plan


def test_plan_reports_informational_total_not_capacity_ceiling():
    # points are a size signal, not a budget — the plan must not impose a capacity ceiling
    plan = _section("plan")
    assert "capacity" not in plan.lower()
    assert "informational" in plan.lower()


def test_scrum_master_spec_drops_capacity_verdict():
    sm = open(os.path.join(ROOT, "agents", "scrum-master.md")).read()
    assert "CAPACITY:" not in sm
    assert "over- or under-committed" not in sm
    assert "informational" in sm.lower()
