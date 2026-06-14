import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "scrum_state.py")


def test_default_config_has_local_visibility():
    assert scrum_state.DEFAULT_CONFIG["scrum_visibility"] == "local"


def test_sync_gitignore_local_adds_all_three(tmp_path):
    (tmp_path / ".git").mkdir()
    scrum_state.save_config(str(tmp_path), dict(scrum_state.DEFAULT_CONFIG))
    scrum_state.sync_gitignore(str(tmp_path))
    text = (tmp_path / ".gitignore").read_text()
    assert ".scrum/" in text
    assert ".serena/" in text
    assert ".codegraph/" in text


def test_sync_gitignore_shared_omits_scrum(tmp_path):
    (tmp_path / ".git").mkdir()
    cfg = dict(scrum_state.DEFAULT_CONFIG)
    cfg["scrum_visibility"] = "shared"
    scrum_state.save_config(str(tmp_path), cfg)
    scrum_state.sync_gitignore(str(tmp_path))
    text = (tmp_path / ".gitignore").read_text()
    assert ".serena/" in text
    assert ".codegraph/" in text
    assert ".scrum/" not in text


def test_sync_gitignore_idempotent(tmp_path):
    (tmp_path / ".git").mkdir()
    scrum_state.save_config(str(tmp_path), dict(scrum_state.DEFAULT_CONFIG))
    scrum_state.sync_gitignore(str(tmp_path))
    first = (tmp_path / ".gitignore").read_text()
    scrum_state.sync_gitignore(str(tmp_path))
    second = (tmp_path / ".gitignore").read_text()
    assert first == second


def test_sync_gitignore_preserves_unrelated_lines(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("__pycache__/\n.scrum/\n")
    cfg = dict(scrum_state.DEFAULT_CONFIG)
    cfg["scrum_visibility"] = "shared"
    scrum_state.save_config(str(tmp_path), cfg)
    scrum_state.sync_gitignore(str(tmp_path))
    text = (tmp_path / ".gitignore").read_text()
    assert "__pycache__/" in text
    assert ".scrum/" not in text


def test_cli_init_scrum_mode_shared(tmp_path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, SCRIPT, "init", "--scrum-mode", "shared"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["scrum_visibility"] == "shared"
    text = (tmp_path / ".gitignore").read_text()
    assert ".scrum/" not in text
    assert ".serena/" in text


def test_sync_gitignore_no_trailing_newline(tmp_path):
    (tmp_path / ".git").mkdir()
    gi = tmp_path / ".gitignore"
    gi.write_text("__pycache__/")  # intentionally no trailing newline
    scrum_state.save_config(str(tmp_path), dict(scrum_state.DEFAULT_CONFIG))
    scrum_state.sync_gitignore(str(tmp_path))
    content = gi.read_text()
    lines = content.splitlines()
    assert "__pycache__/" in lines
    assert ".serena/" in lines
    assert ".codegraph/" in lines
    assert ".scrum/" in lines
    # idempotency: second run must be byte-identical
    scrum_state.sync_gitignore(str(tmp_path))
    assert gi.read_text() == content


def test_cli_init_scrum_mode_local(tmp_path):
    (tmp_path / ".git").mkdir()
    result = subprocess.run(
        [sys.executable, SCRIPT, "init", "--scrum-mode", "local"],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["scrum_visibility"] == "local"
    text = (tmp_path / ".gitignore").read_text()
    assert ".scrum/" in text
