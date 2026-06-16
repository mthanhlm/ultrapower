import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DONE = os.path.join(ROOT, "commands", "done.md")


def _body():
    assert os.path.isfile(DONE), f"commands/done.md not found at {DONE}"
    return open(DONE).read()


def test_done_file_exists():
    assert os.path.isfile(DONE)


def test_done_auto_marks_via_writer_not_hand_edit():
    # the close step drives the mark-done writer rather than hand-editing sprint.md
    assert "mark-done" in _body()


def test_gate_precedes_state_write():
    # auto-bookkeeping must come AFTER the done-gate in the documented flow
    body = _body()
    gate = body.find("done-gate.py")
    write = body.find("mark-done")
    assert gate != -1, "done-gate step missing"
    assert write != -1, "mark-done writer call missing"
    assert gate < write, "the done-gate must run before any state is written"


def test_no_write_on_red_gate_documented():
    # the gate stays a hard gate: nothing closes / no state is written on a red gate
    body = _body().lower()
    assert "red gate" in body
    assert "only after both pass" in body


def test_offers_learn_after_close():
    # after a successful close, /up:done offers (never forces) /up:tutor on the finished story
    assert "/up:tutor" in _body()


def test_done_queues_story_for_tutoring():
    # going fast must not lose the chance to understand — done queues the story (pending, not skip)
    assert "tutor-pending" in _body()
