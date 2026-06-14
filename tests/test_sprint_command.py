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
