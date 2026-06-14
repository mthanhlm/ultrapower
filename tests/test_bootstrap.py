import os
import re
import subprocess
import sys
import types

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INIT_MD = os.path.join(ROOT, "commands", "init.md")


def _make_proc(returncode, stdout="", stderr=""):
    proc = types.SimpleNamespace()
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# --- bootstrap_tools unit tests ---

def test_bootstrap_success_returns_ok_true(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return _make_proc(0, stdout="indexed ok")

    monkeypatch.setattr(subprocess, "run", fake_run)
    results = scrum_state.bootstrap_tools(str(tmp_path))
    assert len(results) == 2
    for rec in results:
        assert rec["ok"] is True


def test_bootstrap_nonzero_returns_ok_false_no_raise(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        return _make_proc(1, stdout="", stderr="error detail")

    monkeypatch.setattr(subprocess, "run", fake_run)
    # must NOT raise
    results = scrum_state.bootstrap_tools(str(tmp_path))
    assert len(results) == 2
    for rec in results:
        assert rec["ok"] is False
        assert "error detail" in rec["output"]


def test_bootstrap_oserror_returns_ok_false_no_raise(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise OSError("no such file")

    monkeypatch.setattr(subprocess, "run", fake_run)
    results = scrum_state.bootstrap_tools(str(tmp_path))
    assert len(results) == 2
    for rec in results:
        assert rec["ok"] is False


def test_bootstrap_file_not_found_no_raise(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise FileNotFoundError("codegraph not found")

    monkeypatch.setattr(subprocess, "run", fake_run)
    results = scrum_state.bootstrap_tools(str(tmp_path))
    for rec in results:
        assert rec["ok"] is False


def test_bootstrap_timeout_no_raise(tmp_path, monkeypatch):
    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd, 30)

    monkeypatch.setattr(subprocess, "run", fake_run)
    results = scrum_state.bootstrap_tools(str(tmp_path))
    for rec in results:
        assert rec["ok"] is False


def test_bootstrap_invokes_codegraph_init(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _make_proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    scrum_state.bootstrap_tools(str(tmp_path))
    assert ["codegraph", "init", str(tmp_path)] in calls


def test_bootstrap_invokes_serena_project_create(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _make_proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    scrum_state.bootstrap_tools(str(tmp_path))
    assert ["serena", "project", "create", str(tmp_path)] in calls


def test_bootstrap_does_not_invoke_serena_init(tmp_path, monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        return _make_proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    scrum_state.bootstrap_tools(str(tmp_path))
    for call in calls:
        assert not (call[:2] == ["serena", "init"]), "serena init must not be used"


def test_bootstrap_result_has_name_ok_output_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _make_proc(0))
    results = scrum_state.bootstrap_tools(str(tmp_path))
    for rec in results:
        assert "name" in rec
        assert "ok" in rec
        assert "output" in rec


def test_bootstrap_result_names(tmp_path, monkeypatch):
    monkeypatch.setattr(subprocess, "run", lambda cmd, **kw: _make_proc(0))
    results = scrum_state.bootstrap_tools(str(tmp_path))
    names = [r["name"] for r in results]
    assert "codegraph" in names
    assert "serena" in names


def test_bootstrap_subprocess_called_with_cwd(tmp_path, monkeypatch):
    kwarg_cwds = []

    def fake_run(cmd, **kwargs):
        kwarg_cwds.append(kwargs.get("cwd"))
        return _make_proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    scrum_state.bootstrap_tools(str(tmp_path))
    for cwd in kwarg_cwds:
        assert cwd == str(tmp_path)


def test_bootstrap_subprocess_called_with_capture(tmp_path, monkeypatch):
    kwargs_list = []

    def fake_run(cmd, **kwargs):
        kwargs_list.append(kwargs)
        return _make_proc(0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    scrum_state.bootstrap_tools(str(tmp_path))
    for kw in kwargs_list:
        assert kw.get("capture_output") is True
        assert kw.get("text") is True


def test_bootstrap_mixed_success_failure(tmp_path, monkeypatch):
    call_count = [0]

    def fake_run(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _make_proc(0, stdout="ok")
        return _make_proc(2, stderr="fail")

    monkeypatch.setattr(subprocess, "run", fake_run)
    results = scrum_state.bootstrap_tools(str(tmp_path))
    ok_vals = [r["ok"] for r in results]
    assert True in ok_vals
    assert False in ok_vals


# --- structural test: init.md references bootstrap ---

def test_init_md_references_bootstrap_step(tmp_path):
    body = open(INIT_MD).read()
    assert re.search(r"bootstrap", body, re.IGNORECASE), (
        "commands/init.md must reference a bootstrap step"
    )


def test_init_md_references_codegraph(tmp_path):
    body = open(INIT_MD).read()
    assert "codegraph" in body, "commands/init.md must mention codegraph in the bootstrap step"


def test_init_md_references_serena_project(tmp_path):
    body = open(INIT_MD).read()
    assert re.search(r"serena\s+project\s+create", body), (
        "commands/init.md must reference 'serena project create'"
    )


def test_init_md_bootstrap_is_nonfatal(tmp_path):
    body = open(INIT_MD).read()
    assert re.search(r"non.fatal|does not abort|not abort|failure.*does not|continue", body, re.IGNORECASE), (
        "commands/init.md must note that bootstrap failure is non-fatal"
    )
