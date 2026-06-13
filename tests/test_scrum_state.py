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
    assert cfg["sprint_length_days"] == 7
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
        [sys.executable, SCRIPT, "init", "--test", "pytest -q", "--sprint-days", "14"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["verify"]["test"] == "pytest -q"
    assert cfg["sprint_length_days"] == 14
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


def test_cli_close_clears_current_story(tmp_path):
    (tmp_path / ".git").mkdir()
    src = tmp_path / "a.py"
    src.write_text("x = 1\n")
    base = [sys.executable, SCRIPT]
    subprocess.run(base + ["lock", "--id", "S1", "--file", str(src)], cwd=str(tmp_path),
                   capture_output=True, text=True, check=True)
    subprocess.run(base + ["close"], cwd=str(tmp_path), capture_output=True, text=True, check=True)
    assert not (tmp_path / ".scrum" / "current-story.json").exists()
