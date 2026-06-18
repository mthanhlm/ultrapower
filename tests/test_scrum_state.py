import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "scrum_state.py")


def test_find_project_root_uses_git_marker(tmp_path):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert scrum_state.find_project_root(str(nested)) == os.path.realpath(str(tmp_path))


def test_config_defaults_when_missing(tmp_path):
    cfg = scrum_state.load_config(str(tmp_path))
    assert "sprint_length_days" not in cfg
    assert "test" in cfg["verify"]


def test_loaded_config_does_not_leak_into_default(tmp_path):
    cfg = scrum_state.load_config(str(tmp_path))
    cfg["verify"]["test"] = "pytest -q"
    scrum_state.save_config(str(tmp_path), cfg)
    assert scrum_state.load_config(str(tmp_path))["verify"]["test"] == "pytest -q"
    assert scrum_state.DEFAULT_CONFIG["verify"]["test"] == ""


def test_current_story_round_trip(tmp_path):
    assert scrum_state.load_current_story(str(tmp_path)) is None
    scrum_state.save_current_story(str(tmp_path), {"id": "S1", "files": ["/x/a.py"]})
    assert scrum_state.load_current_story(str(tmp_path))["id"] == "S1"
    scrum_state.clear_current_story(str(tmp_path))
    assert scrum_state.load_current_story(str(tmp_path)) is None


def test_cli_init_writes_config_and_scaffold(tmp_path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, SCRIPT, "init", "--test", "pytest -q"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["verify"]["test"] == "pytest -q"
    assert "sprint_length_days" not in cfg
    for name in ("backlog.md", "sprint.md", "velocity.md", "retro.md"):
        assert (tmp_path / ".scrum" / name).is_file()


def test_cli_init_preserves_existing_without_force(tmp_path):
    (tmp_path / ".git").mkdir()
    base = [sys.executable, SCRIPT, "init"]
    subprocess.run(base + ["--test", "first"], cwd=str(tmp_path), capture_output=True, text=True)
    subprocess.run(base + ["--test", "second"], cwd=str(tmp_path), capture_output=True, text=True)
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["verify"]["test"] == "first"


def test_cli_lock_writes_current_story(tmp_path):
    (tmp_path / ".git").mkdir()
    src = tmp_path / "a.py"
    src.write_text("x = 1\n")
    result = subprocess.run(
        [sys.executable, SCRIPT, "lock", "--id", "S3", "--title", "do a thing",
         "--points", "3", "--file", str(src), "--acceptance", "it works"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    assert story["id"] == "S3"
    assert story["red_test_observed"] is False
    assert story["status"] == "in-progress"
    assert story["files"] == [os.path.realpath(str(src))]


def test_cli_mark_red_sets_flag(tmp_path):
    (tmp_path / ".git").mkdir()
    src = tmp_path / "a.py"
    src.write_text("x = 1\n")
    base = [sys.executable, SCRIPT]
    subprocess.run(base + ["lock", "--id", "S1", "--file", str(src)], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    subprocess.run(base + ["mark-red"], cwd=str(tmp_path), capture_output=True, text=True, check=True)
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    assert story["red_test_observed"] is True


def test_cli_add_file_extends_contract(tmp_path):
    (tmp_path / ".git").mkdir()
    a = tmp_path / "a.py"
    a.write_text("x = 1\n")
    b = tmp_path / "b.py"
    b.write_text("y = 2\n")
    base = [sys.executable, SCRIPT]
    subprocess.run(base + ["lock", "--id", "S1", "--file", str(a)], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    subprocess.run(base + ["add-file", "--file", str(b)], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    assert os.path.realpath(str(b)) in story["files"]


def test_cli_lock_root_anchors_relative_file_from_subdir(tmp_path):
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    result = subprocess.run(
        [sys.executable, SCRIPT, "lock", "--id", "S9", "--title", "subdir test",
         "--points", "1", "--file", "tests/foo.py", "--acceptance", "path anchored"],
        cwd=str(subdir), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    expected = os.path.realpath(str(tmp_path / "tests" / "foo.py"))
    assert story["files"] == [expected], f"got {story['files']!r}, want {[expected]!r}"


def test_cli_add_file_root_anchors_relative_file_from_subdir(tmp_path):
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    base = [sys.executable, SCRIPT]
    subprocess.run(
        base + ["lock", "--id", "S9", "--file", "a.py"],
        cwd=str(subdir), capture_output=True, text=True, check=True,
    )
    subprocess.run(
        base + ["add-file", "--file", "b.py"],
        cwd=str(subdir), capture_output=True, text=True, check=True,
    )
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    expected_b = os.path.realpath(str(tmp_path / "b.py"))
    assert expected_b in story["files"], f"got {story['files']!r}, want {expected_b!r} anchored to root"


def test_cli_close_clears_current_story(tmp_path):
    (tmp_path / ".git").mkdir()
    src = tmp_path / "a.py"
    src.write_text("x = 1\n")
    base = [sys.executable, SCRIPT]
    subprocess.run(base + ["lock", "--id", "S1", "--file", str(src)], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    subprocess.run(base + ["close"], cwd=str(tmp_path), capture_output=True, text=True, check=True)
    assert not (tmp_path / ".scrum" / "current-story.json").exists()


def _write_sprint(tmp_path, rows):
    scrum_state.ensure_scrum(str(tmp_path))
    body = "# Current Sprint\n\n| ID | Story | Points | Status |\n|----|-------|--------|--------|\n" + rows
    (tmp_path / ".scrum" / "sprint.md").write_text(body)
    return tmp_path / ".scrum" / "sprint.md"


def test_mark_story_done_flips_only_its_row(tmp_path):
    sprint = _write_sprint(tmp_path, "| S1 | first | 3 | todo |\n| S2 | second | 5 | in-progress |\n")
    assert scrum_state.mark_story_done(str(tmp_path), "S2") is True
    body = sprint.read_text()
    assert "| S2 | second | 5 | done |" in body
    assert "| S1 | first | 3 | todo |" in body


def test_mark_story_done_idempotent_and_missing_id(tmp_path):
    sprint = _write_sprint(tmp_path, "| S1 | first | 3 | todo |\n")
    assert scrum_state.mark_story_done(str(tmp_path), "S1") is True
    once = sprint.read_text()
    assert scrum_state.mark_story_done(str(tmp_path), "S1") is True
    assert sprint.read_text() == once
    assert scrum_state.mark_story_done(str(tmp_path), "S9") is False


def test_record_velocity_appends_then_upserts(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    vel = tmp_path / ".scrum" / "velocity.md"
    vel.write_text(scrum_state.SCAFFOLD["velocity.md"])
    assert scrum_state.record_velocity(str(tmp_path), "2", "ship it", 40, 11) is True
    assert "| 2 | ship it | 40 | 11 |" in vel.read_text()
    assert scrum_state.record_velocity(str(tmp_path), "2", "ship it", 40, 26) is False
    body = vel.read_text()
    assert "| 2 | ship it | 40 | 26 |" in body
    assert body.count("| 2 |") == 1


def test_cli_mark_done_and_record_velocity(tmp_path):
    sprint = _write_sprint(tmp_path, "| S7 | a story | 2 | in-progress |\n")
    (tmp_path / ".scrum" / "velocity.md").write_text(scrum_state.SCAFFOLD["velocity.md"])
    base = [sys.executable, SCRIPT]
    r1 = subprocess.run(base + ["mark-done", "--id", "S7"], cwd=str(tmp_path),
                        capture_output=True, text=True)
    assert r1.returncode == 0, r1.stderr
    assert "| S7 | a story | 2 | done |" in sprint.read_text()
    r2 = subprocess.run(base + ["record-velocity", "--sprint", "3", "--goal", "g",
                                "--committed", "9", "--completed", "9"],
                        cwd=str(tmp_path), capture_output=True, text=True)
    assert r2.returncode == 0, r2.stderr
    assert "| 3 | g | 9 | 9 |" in (tmp_path / ".scrum" / "velocity.md").read_text()


def test_draft_retro_appends_newest_first_and_preserves(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    retro = tmp_path / ".scrum" / "retro.md"
    retro.write_text("# Retrospectives\n\n## 2026-01-01 — Sprint 1 (old)\n\nkeep me\n")
    assert scrum_state.draft_retro(str(tmp_path), "2", "ship it", 40, 26) is True
    body = retro.read_text()
    assert "## Sprint 2 — DRAFT" in body
    assert "Learned" in body
    assert "keep me" in body
    assert body.index("## Sprint 2 — DRAFT") < body.index("## 2026-01-01 — Sprint 1")


def test_draft_retro_dedupes_per_sprint(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    retro = tmp_path / ".scrum" / "retro.md"
    retro.write_text(scrum_state.SCAFFOLD["retro.md"])
    assert scrum_state.draft_retro(str(tmp_path), "2", "g", 5, 5) is True
    first = retro.read_text()
    assert scrum_state.draft_retro(str(tmp_path), "2", "g", 5, 5) is False
    assert retro.read_text() == first
    assert first.count("## Sprint 2 —") == 1


def test_cli_draft_retro(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    (tmp_path / ".scrum" / "retro.md").write_text(scrum_state.SCAFFOLD["retro.md"])
    r = subprocess.run([sys.executable, SCRIPT, "draft-retro", "--sprint", "2",
                        "--goal", "g", "--committed", "5", "--completed", "5"],
                       cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "## Sprint 2 — DRAFT" in (tmp_path / ".scrum" / "retro.md").read_text()


def test_scaffold_creates_tutored_md(tmp_path):
    assert "tutored.md" in scrum_state.SCAFFOLD
    scrum_state.scaffold(str(tmp_path))
    assert (tmp_path / ".scrum" / "tutored.md").is_file()


def test_record_learning_dedupes_within_source(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    learned = tmp_path / ".scrum" / "tutored.md"
    learned.write_text(scrum_state.SCAFFOLD["tutored.md"])
    assert scrum_state.record_learning(str(tmp_path), "project", "Event loop basics", "why") is True
    assert scrum_state.record_learning(str(tmp_path), "project", "event loop BASICS") is False
    body = learned.read_text()
    assert body.count("Event loop basics") == 1
    assert "## project" in body


def test_record_learning_separate_per_source(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    learned = tmp_path / ".scrum" / "tutored.md"
    learned.write_text(scrum_state.SCAFFOLD["tutored.md"])
    assert scrum_state.record_learning(str(tmp_path), "project", "Topic A") is True
    assert scrum_state.record_learning(str(tmp_path), "S4", "Topic A") is True
    body = learned.read_text()
    assert "## project" in body and "## S4" in body
    assert body.count("Topic A") == 2


def test_cli_record_learning(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    (tmp_path / ".scrum" / "tutored.md").write_text(scrum_state.SCAFFOLD["tutored.md"])
    r = subprocess.run([sys.executable, SCRIPT, "record-learning", "--source", "project",
                        "--topic", "TDD red-green", "--note", "write the test first"],
                       cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "TDD red-green" in (tmp_path / ".scrum" / "tutored.md").read_text()


def test_queue_tutor_add_list_dedupe_remove(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    tutored = tmp_path / ".scrum" / "tutored.md"
    tutored.write_text(scrum_state.SCAFFOLD["tutored.md"])
    assert scrum_state.queue_tutor(str(tmp_path), "S3", "ceiling") is True
    assert scrum_state.queue_tutor(str(tmp_path), "S3", "ceiling") is False
    assert scrum_state.list_pending(str(tmp_path)) == ["S3"]
    body = tutored.read_text()
    assert "## Pending" in body and "- S3 — ceiling" in body
    assert scrum_state.unqueue_tutor(str(tmp_path), "S3") is True
    assert scrum_state.list_pending(str(tmp_path)) == []
    assert scrum_state.unqueue_tutor(str(tmp_path), "S3") is False


def test_pending_and_learnings_stay_separate(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    tutored = tmp_path / ".scrum" / "tutored.md"
    tutored.write_text(scrum_state.SCAFFOLD["tutored.md"])
    scrum_state.queue_tutor(str(tmp_path), "S3", "ceiling")
    scrum_state.record_learning(str(tmp_path), "S3", "size signal not budget")
    body = tutored.read_text()
    assert "## Pending" in body and "## S3" in body
    assert "size signal not budget" in body
    assert scrum_state.list_pending(str(tmp_path)) == ["S3"]


def test_cli_tutor_pending(tmp_path):
    scrum_state.ensure_scrum(str(tmp_path))
    (tmp_path / ".scrum" / "tutored.md").write_text(scrum_state.SCAFFOLD["tutored.md"])
    base = [sys.executable, SCRIPT]
    subprocess.run(base + ["tutor-pending", "--add", "S6", "--title", "wire done"],
                   cwd=str(tmp_path), capture_output=True, text=True, check=True)
    out = subprocess.run(base + ["tutor-pending", "--list"], cwd=str(tmp_path),
                         capture_output=True, text=True)
    assert "S6" in out.stdout
    subprocess.run(base + ["tutor-pending", "--remove", "S6"], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    out2 = subprocess.run(base + ["tutor-pending", "--list"], cwd=str(tmp_path),
                          capture_output=True, text=True)
    assert "S6" not in out2.stdout


def test_ladder_text_returns_body():
    body = scrum_state.ladder_text()
    assert "Does this need to exist" in body


def test_ladder_file_exists_and_has_rungs():
    assert os.path.isfile(scrum_state._LADDER_PATH)
    body = open(scrum_state._LADDER_PATH).read()
    for rung in ("Stdlib does it", "one line", "minimum code that works"):
        assert rung in body


def test_lean_debt_parses_marker(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("x = 1  # lean: global lock, per-account if hot\n")
    ledger = scrum_state.scan_lean_debt(str(tmp_path), [str(f)])
    assert len(ledger) == 1
    row = ledger[0]
    assert row["file"] == "m.py" and row["line"] == 1
    assert row["ceiling"] == "global lock"
    assert row["upgrade"] == "per-account if hot"
    assert row["no_trigger"] is False


def test_lean_debt_flags_no_trigger(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("# lean: naive O(n^2) scan\nx = 1\n")
    ledger = scrum_state.scan_lean_debt(str(tmp_path), [str(f)])
    assert len(ledger) == 1
    assert ledger[0]["ceiling"] == "naive O(n^2) scan"
    assert ledger[0]["no_trigger"] is True


def test_lean_debt_empty_when_no_markers(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("x = 1\n# just a normal comment\n")
    assert scrum_state.scan_lean_debt(str(tmp_path), [str(f)]) == []


def test_scan_lean_debt_whole_repo_via_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, text=True)
    (tmp_path / "a.py").write_text("# lean: stub, fix when X lands\nx = 1\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, text=True)
    ledger = scrum_state.scan_lean_debt(str(tmp_path))
    assert any(r["file"] == "a.py" for r in ledger)


def test_cli_lean_debt(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "m.py").write_text("# lean: stub, real impl when needed\nx = 1\n")
    subprocess.run([sys.executable, SCRIPT, "init", "--force"], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    out = subprocess.run([sys.executable, SCRIPT, "lean-debt", "--file", "m.py"],
                         cwd=str(tmp_path), capture_output=True, text=True)
    assert "m.py" in out.stdout
    assert "1 marker" in out.stdout
