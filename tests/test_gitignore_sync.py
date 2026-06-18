import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "scrum_state.py")


def test_default_config_has_no_visibility_key():
    # .scrum/ is always local now — visibility config was deleted (deletion over config).
    assert "scrum_visibility" not in scrum_state.DEFAULT_CONFIG


def test_sync_gitignore_adds_all_three(tmp_path):
    (tmp_path / ".git").mkdir()
    scrum_state.sync_gitignore(str(tmp_path))
    text = (tmp_path / ".gitignore").read_text()
    assert ".scrum/" in text and ".serena/" in text and ".codegraph/" in text


def test_sync_gitignore_idempotent(tmp_path):
    (tmp_path / ".git").mkdir()
    scrum_state.sync_gitignore(str(tmp_path))
    first = (tmp_path / ".gitignore").read_text()
    scrum_state.sync_gitignore(str(tmp_path))
    assert (tmp_path / ".gitignore").read_text() == first


def test_sync_gitignore_preserves_unrelated_lines(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("__pycache__/\nnode_modules/\n")
    scrum_state.sync_gitignore(str(tmp_path))
    text = (tmp_path / ".gitignore").read_text()
    assert "__pycache__/" in text and "node_modules/" in text and ".scrum/" in text


def test_sync_gitignore_no_trailing_newline(tmp_path):
    (tmp_path / ".git").mkdir()
    gi = tmp_path / ".gitignore"
    gi.write_text("__pycache__/")  # intentionally no trailing newline
    scrum_state.sync_gitignore(str(tmp_path))
    lines = gi.read_text().splitlines()
    for entry in ("__pycache__/", ".serena/", ".codegraph/", ".scrum/"):
        assert entry in lines
    content = gi.read_text()
    scrum_state.sync_gitignore(str(tmp_path))
    assert gi.read_text() == content  # byte-identical second run


def test_cli_init_gitignores_scrum(tmp_path):
    (tmp_path / ".git").mkdir()
    import subprocess
    r = subprocess.run([sys.executable, SCRIPT, "init"], cwd=str(tmp_path), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert ".scrum/" in (tmp_path / ".gitignore").read_text()
