import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")


def _body():
    assert os.path.isfile(README), f"README.md not found at {README}"
    return open(README).read()


def test_file_exists():
    assert os.path.isfile(README)


def test_three_verb_surface_documented():
    body = _body()
    for cmd in ("/up:init", "/up:plan", "/up:run", "/up:status"):
        assert cmd in body, f"{cmd} missing from README"


def test_no_dangling_scrum_features():
    # The Scrum ceremony + tutor + the never-shipped /up:lean must be gone from the docs.
    body = _body()
    for dead in ("/up:sprint", "/up:story", "/up:done", "/up:tutor", "/up:lean", "lean_mode", "velocity"):
        assert dead not in body, f"dangling reference to removed feature: {dead}"


def test_agents_table_lists_current_three():
    body = _body()
    for agent in ("step-planner", "implementer", "navigator"):
        assert re.search(rf"(?m)^\|\s*`?{re.escape(agent)}`?\s*\|", body), f"agent row '{agent}' missing"
    # debate / scrum-master / teacher are deleted
    for gone in ("debate", "scrum-master", "teacher"):
        assert not re.search(rf"(?m)^\|\s*`?{gone}`?\s*\|", body), f"deleted agent '{gone}' still in table"


def test_loop_runs_before_close_and_mentions_decomposition():
    body = _body()
    loop = re.search(r"## The loop\s*```.*?```", body, re.DOTALL)
    assert loop, "## The loop code-fence not found"
    text = loop.group(0)
    assert text.find("/up:plan") < text.find("/up:run"), "plan must precede run in the loop"
    assert "lock" in text and "navigator" in text


def test_loop_mentions_lean_ladder():
    loop = re.search(r"## The loop\s*```.*?```", _body(), re.DOTALL)
    assert loop, "## The loop code-fence not found"
    low = loop.group(0).lower()
    assert "lean" in low and "ladder" in low


def test_plan_guard_is_documented_as_the_forcing_function():
    body = _body().lower()
    assert "plan-guard" in body
    assert "hook fact" in body or "not around it" in body


def test_command_rows_pipe_count_consistent():
    # Literal in-cell pipes must be escaped as \| so the markdown table stays well-formed.
    body = _body()

    def unescaped_pipes(row):
        return len(re.findall(r"(?<!\\)\|", row))

    rows = re.findall(r"(?m)^\|\s*`/up:[^\n]*\|$", body)
    assert len(rows) >= 4, "expected the four command rows"
    counts = {unescaped_pipes(r) for r in rows}
    assert len(counts) == 1, f"command rows have inconsistent delimiter counts: {counts}"
