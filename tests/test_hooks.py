import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOKS = os.path.join(ROOT, "hooks")
STATE = os.path.join(ROOT, "scripts", "scrum_state.py")


def _mk(project, rel, content="x = 1\n"):
    p = project / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


def _run_hook(name, data):
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS, name)],
        input=json.dumps(data), capture_output=True, text=True,
    )


def _lock(project, files, red=False):
    (project / ".git").mkdir(exist_ok=True)
    cmd = [sys.executable, STATE, "lock", "--id", "S1", "--title", "t"]
    for f in files:
        cmd += ["--file", str(f)]
    subprocess.run(cmd, cwd=str(project), capture_output=True, text=True, check=True)
    if red:
        subprocess.run([sys.executable, STATE, "mark-red"], cwd=str(project),
                       capture_output=True, text=True, check=True)


def _edit(project, path):
    return {"cwd": str(project), "tool_name": "Edit", "tool_input": {"file_path": str(path)}}


def test_scope_guard_denies_outside_contract(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    out = _run_hook("scope-guard.py", _edit(tmp_path, _mk(tmp_path, "src/other.py")))
    assert '"permissionDecision": "deny"' in out.stdout


def test_scope_guard_allows_contract_file(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    out = _run_hook("scope-guard.py", _edit(tmp_path, src))
    assert out.stdout.strip() == ""


def test_scope_guard_allows_without_story(tmp_path):
    (tmp_path / ".git").mkdir()
    out = _run_hook("scope-guard.py", _edit(tmp_path, _mk(tmp_path, "src/a.py")))
    assert out.stdout.strip() == ""


def test_tdd_guard_blocks_source_before_red(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=False)
    out = _run_hook("tdd-guard.py", _edit(tmp_path, src))
    assert '"permissionDecision": "deny"' in out.stdout


def test_tdd_guard_allows_test_before_red(tmp_path):
    test = _mk(tmp_path, "tests/test_a.py", "def test_x():\n    assert True\n")
    _lock(tmp_path, [test], red=False)
    out = _run_hook("tdd-guard.py", _edit(tmp_path, test))
    assert out.stdout.strip() == ""


def test_tdd_guard_allows_source_after_red(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    out = _run_hook("tdd-guard.py", _edit(tmp_path, src))
    assert out.stdout.strip() == ""


def test_comment_noise_blocks_narration(tmp_path):
    data = {"tool_input": {"file_path": str(tmp_path / "a.py"),
                           "new_string": "# Loop through the items\nx = 1\n"}}
    out = _run_hook("comment-noise.py", data)
    assert out.returncode == 2
    assert "Narration" in out.stderr


def test_comment_noise_allows_why_note(tmp_path):
    data = {"tool_input": {"file_path": str(tmp_path / "a.py"),
                           "new_string": "# WHY: upstream returns naive datetimes\nx = 1\n"}}
    out = _run_hook("comment-noise.py", data)
    assert out.returncode == 0


def test_comment_noise_keeps_lean_marker(tmp_path):
    data = {"tool_input": {"file_path": str(tmp_path / "a.py"),
                           "new_string": "# lean: global lock, per-account locks if throughput matters\nx = 1\n"}}
    out = _run_hook("comment-noise.py", data)
    assert out.returncode == 0


def test_comment_noise_lean_exemption_beats_narration(tmp_path):
    # Without the lean: exemption this line trips the "update the ..." narration rule.
    data = {"tool_input": {"file_path": str(tmp_path / "a.py"),
                           "new_string": "# update the cache lean: global lock, shard if hot\nx = 1\n"}}
    out = _run_hook("comment-noise.py", data)
    assert out.returncode == 0


def _done_gate(project):
    return subprocess.run([sys.executable, os.path.join(HOOKS, "done-gate.py"), str(project)],
                          capture_output=True, text=True)


def test_done_gate_passes_when_checks_pass(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    subprocess.run([sys.executable, STATE, "init", "--test", "true", "--force"],
                   cwd=str(tmp_path), capture_output=True, text=True, check=True)
    out = _done_gate(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr


def test_done_gate_fails_when_check_fails(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    subprocess.run([sys.executable, STATE, "init", "--test", "false", "--force"],
                   cwd=str(tmp_path), capture_output=True, text=True, check=True)
    out = _done_gate(tmp_path)
    assert out.returncode == 1


def test_done_gate_needs_active_story(tmp_path):
    (tmp_path / ".git").mkdir()
    out = _done_gate(tmp_path)
    assert out.returncode == 1


def _init_lean(project):
    (project / ".git").mkdir(exist_ok=True)
    subprocess.run([sys.executable, STATE, "init", "--force"], cwd=str(project),
                   capture_output=True, text=True, check=True)
    return project


def test_lean_inject_emits_ladder(tmp_path):
    _init_lean(tmp_path)
    out = _run_hook("lean-inject.py", {"cwd": str(tmp_path)})
    assert "Does this need to exist" in out.stdout


def test_lean_inject_silent_without_scrum(tmp_path):
    (tmp_path / ".git").mkdir()
    out = _run_hook("lean-inject.py", {"cwd": str(tmp_path)})
    assert out.stdout.strip() == ""


def test_lean_hooks_fail_open_on_bad_stdin():
    for name in ("lean-inject.py",):
        out = subprocess.run([sys.executable, os.path.join(HOOKS, name)],
                             input="not json", capture_output=True, text=True)
        assert out.returncode == 0, name
