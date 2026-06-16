import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CMD = os.path.join(ROOT, "commands", "tutor.md")


def _body():
    assert os.path.isfile(CMD), f"commands/tutor.md not found at {CMD}"
    return open(CMD).read()


def test_file_exists():
    assert os.path.isfile(CMD)


def test_documents_both_modes():
    low = _body().lower()
    assert "story" in low and "project" in low
    assert "diff" in low


def test_invokes_teacher_agent():
    assert "teacher" in _body()


def test_persists_to_tutored_md_deduped():
    body = _body()
    assert "record-learning" in body
    assert "tutored.md" in body
    assert "dedup" in body.lower()


def test_interactive_quiz_and_mastery():
    low = _body().lower()
    assert "askuserquestion" in low
    assert "master" in low
    assert "restate" in low
    assert "eli5" in low


def test_drains_pending_queue():
    # with no explicit target, /up:tutor works the pending queue and clears items on mastery
    body = _body()
    assert "pending" in body.lower()
    assert "tutor-pending" in body
