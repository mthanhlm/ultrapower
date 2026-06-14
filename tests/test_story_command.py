import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMD = os.path.join(ROOT, "commands", "story.md")


def _body():
    assert os.path.isfile(CMD), f"commands/story.md not found at {CMD}"
    return open(CMD).read()


def test_file_exists():
    assert os.path.isfile(CMD)


def test_debate_agent_invoked():
    body = _body()
    # Must reference debate as an invoked agent, not incidental prose.
    assert re.search(r"(invoke[sd]?\s+the\s+`debate`|`debate`\s+agent)", body, re.IGNORECASE), (
        "story.md must invoke the debate agent explicitly"
    )


def test_debate_before_lock():
    body = _body()
    debate_match = re.search(r"(invoke[sd]?\s+the\s+`debate`|`debate`\s+agent)", body, re.IGNORECASE)
    lock_match = re.search(r"scrum_state\.py.*lock|`lock`\b", body)
    assert debate_match and lock_match, "both debate reference and lock instruction must be present"
    assert debate_match.start() < lock_match.start(), (
        "debate reference must appear before the lock instruction"
    )


def test_gate_vocab_present():
    body = _body()
    # Must carry real gate vocabulary — not just a mention.
    assert "revise-plan" in body, "gate vocab 'revise-plan' missing"
    assert "VERDICT" in body, "gate vocab 'VERDICT' missing"
