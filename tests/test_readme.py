import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")


def _body():
    assert os.path.isfile(README), f"README.md not found at {README}"
    return open(README).read()


def test_file_exists():
    assert os.path.isfile(README)


def test_agents_table_has_debate_row():
    body = _body()
    # Must be a real table row starting with | debate |, not a bare substring.
    assert re.search(r"(?m)^\|\s*`?debate`?\s*\|", body), (
        "Agents table must contain a 'debate' row"
    )


def test_loop_documents_debate_review():
    body = _body()
    # debate must co-occur with at least one of the gate-vocab words in the file.
    gate_words = re.compile(r"proceed|revise-plan|pre-lock|plan review", re.IGNORECASE)
    assert re.search(r"\bdebate\b", body) and gate_words.search(body), (
        "'debate' and at least one of proceed|revise-plan|pre-lock|plan review must appear in README"
    )


def test_debate_appears_before_lock_in_loop():
    body = _body()
    # Locate the loop fence — from "The loop" heading to end of its code block.
    loop_match = re.search(r"## The loop\s*```.*?```", body, re.DOTALL)
    assert loop_match, "## The loop code-fence not found"
    loop_text = loop_match.group(0)
    debate_pos = loop_text.find("debate")
    lock_pos = re.search(r"\block\b|done\b", loop_text)
    assert debate_pos != -1, "'debate' not found in the loop fence"
    assert lock_pos is not None, "lock/done marker not found in loop fence"
    assert debate_pos < lock_pos.start(), (
        "'debate' must appear before 'lock'/'done' in the loop fence"
    )


def test_debate_row_pipe_count_matches_sibling():
    body = _body()
    # Unescaped | (not preceded by \) acts as a column delimiter; literal in-cell
    # pipes must be escaped as \| so the column count stays consistent.
    def unescaped_pipe_count(row: str) -> int:
        return len(re.findall(r"(?<!\\)\|", row))

    debate_row = re.search(r"(?m)^\|[^\n]*`debate`[^\n]*\|$", body)
    navigator_row = re.search(r"(?m)^\|[^\n]*`navigator`[^\n]*\|$", body)
    assert debate_row, "debate row not found in Agents table"
    assert navigator_row, "navigator row not found in Agents table"
    assert unescaped_pipe_count(debate_row.group(0)) == unescaped_pipe_count(navigator_row.group(0)), (
        "debate row has a different number of unescaped '|' delimiters than the navigator row — "
        "escape any literal in-cell pipes as \\|"
    )


def test_loop_mentions_lean_ladder():
    body = _body()
    loop_match = re.search(r"## The loop\s*```.*?```", body, re.DOTALL)
    assert loop_match, "## The loop code-fence not found"
    loop = loop_match.group(0).lower()
    assert "lean" in loop and "ladder" in loop, "the loop must mention the lean ladder"


def test_debate_described_as_six_lenses():
    # S5/S6 made debate + navigator six lenses; the README wording must match.
    assert "five lenses" not in _body(), "debate is now six lenses — reconcile the README wording"
