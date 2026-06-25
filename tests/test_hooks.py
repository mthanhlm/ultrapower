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


def _state(project, *args):
    subprocess.run([sys.executable, STATE, *args], cwd=str(project),
                   capture_output=True, text=True, check=True)


def _lock(project, files, red=False):
    (project / ".git").mkdir(exist_ok=True)
    cmd = ["lock", "--id", "1", "--title", "t"]
    for f in files:
        cmd += ["--file", str(f)]
    _state(project, *cmd)
    if red:
        _state(project, "mark-red")


def _plan(project, *step_ids):
    (project / ".git").mkdir(exist_ok=True)
    _state(project, "plan-new", "--task", "t")
    for sid in step_ids:
        _state(project, "plan-add", "--id", sid, "--title", f"step {sid}")


def _edit(project, path):
    return {"cwd": str(project), "tool_name": "Edit", "tool_input": {"file_path": str(path)}}


# --- scope-guard -------------------------------------------------------------

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


# --- tdd-guard (per-criterion latch reads red_criteria) ----------------------

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


def test_tdd_guard_inert_for_refactor_kind(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    (tmp_path / ".git").mkdir(exist_ok=True)
    _state(tmp_path, "lock", "--id", "1", "--file", str(src), "--kind", "refactor")
    out = _run_hook("tdd-guard.py", _edit(tmp_path, src))
    assert out.stdout.strip() == ""


# --- plan-guard (decomposition is a hook fact) -------------------------------

def test_plan_guard_denies_source_edit_when_plan_unfinished_and_no_lock(tmp_path):
    _plan(tmp_path, "1", "2")
    out = _run_hook("plan-guard.py", _edit(tmp_path, _mk(tmp_path, "src/a.py")))
    assert '"permissionDecision": "deny"' in out.stdout


def test_plan_guard_allows_when_step_locked(tmp_path):
    _plan(tmp_path, "1")
    src = _mk(tmp_path, "src/a.py")
    _state(tmp_path, "lock", "--id", "1", "--file", str(src))
    out = _run_hook("plan-guard.py", _edit(tmp_path, src))
    assert out.stdout.strip() == ""


def test_plan_guard_allows_non_code_files(tmp_path):
    _plan(tmp_path, "1")
    out = _run_hook("plan-guard.py", _edit(tmp_path, _mk(tmp_path, "README.md", "# docs\n")))
    assert out.stdout.strip() == ""


def test_plan_guard_allows_test_files(tmp_path):
    _plan(tmp_path, "1")
    out = _run_hook("plan-guard.py", _edit(tmp_path, _mk(tmp_path, "tests/test_a.py")))
    assert out.stdout.strip() == ""


def test_plan_guard_inert_without_plan(tmp_path):
    (tmp_path / ".git").mkdir()
    out = _run_hook("plan-guard.py", _edit(tmp_path, _mk(tmp_path, "src/a.py")))
    assert out.stdout.strip() == ""


def test_plan_guard_inert_when_plan_complete(tmp_path):
    _plan(tmp_path, "1")
    _state(tmp_path, "step-status", "--id", "1", "--status", "done")
    out = _run_hook("plan-guard.py", _edit(tmp_path, _mk(tmp_path, "src/a.py")))
    assert out.stdout.strip() == ""


def test_plan_guard_fail_open_on_bad_stdin():
    out = subprocess.run([sys.executable, os.path.join(HOOKS, "plan-guard.py")],
                         input="not json", capture_output=True, text=True)
    assert out.returncode == 0


# --- done-gate (parallel verify set) -----------------------------------------

def _done_gate(project):
    return subprocess.run([sys.executable, os.path.join(HOOKS, "done-gate.py"), str(project)],
                          capture_output=True, text=True)


def test_done_gate_passes_when_checks_pass(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    _state(tmp_path, "init", "--test", "true", "--force")
    out = _done_gate(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr


def test_done_gate_fails_when_check_fails(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    _state(tmp_path, "init", "--test", "false", "--force")
    assert _done_gate(tmp_path).returncode == 1


def test_done_gate_runs_checks_in_parallel(tmp_path):
    # Two ~1s sleeps must finish well under 2s if truly parallel.
    import time
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    _state(tmp_path, "init", "--test", "sleep 1", "--lint", "sleep 1", "--force")
    start = time.monotonic()
    out = _done_gate(tmp_path)
    assert out.returncode == 0, out.stdout + out.stderr
    assert time.monotonic() - start < 1.8, "checks did not run in parallel"


def test_done_gate_needs_active_step(tmp_path):
    (tmp_path / ".git").mkdir()
    assert _done_gate(tmp_path).returncode == 1


def _done_gate_checks(project, checks):
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS, "done-gate.py"), str(project), "--checks", checks],
        capture_output=True, text=True,
    )


def test_done_gate_checks_subset_runs_only_named(tmp_path):
    # test would fail, lint would pass; restrict to lint -> the failing test is skipped, gate passes.
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    _state(tmp_path, "init", "--test", "false", "--lint", "true", "--force")
    out = _done_gate_checks(tmp_path, "lint")
    assert out.returncode == 0, out.stdout + out.stderr


def test_done_gate_checks_subset_excludes_unnamed(tmp_path):
    # restrict to test -> the failing test is the only check that runs -> gate fails.
    src = _mk(tmp_path, "src/a.py")
    _lock(tmp_path, [src], red=True)
    _state(tmp_path, "init", "--test", "false", "--lint", "true", "--force")
    assert _done_gate_checks(tmp_path, "test").returncode == 1


# --- lean-inject -------------------------------------------------------------

def _init_lean(project):
    (project / ".git").mkdir(exist_ok=True)
    _state(project, "init", "--force")
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
    for name in ("lean-inject.py", "gitignore-sync.py"):
        out = subprocess.run([sys.executable, os.path.join(HOOKS, name)],
                             input="not json", capture_output=True, text=True)
        assert out.returncode == 0, name


# --- bash-guard (Bash can't write source around the edit guards) -------------

def _bash(project, command):
    return _run_hook("bash-guard.py", {"cwd": str(project),
                                       "tool_name": "Bash", "tool_input": {"command": command}})


def _denied(out):
    return '"permissionDecision": "deny"' in out.stdout


def test_bash_guard_denies_shell_source_write_when_plan_unfinished(tmp_path):
    _plan(tmp_path, "1")
    for cmd in ("echo 'code' > src/a.py", "cat <<EOF >> src/a.py\nx\nEOF",
                "sed -i 's/a/b/' src/a.py", "tee src/a.py", "cp /tmp/x src/a.py"):
        assert _denied(_bash(tmp_path, cmd)), cmd


def test_bash_guard_allows_verify_and_read_commands(tmp_path):
    _plan(tmp_path, "1")
    for cmd in ("pytest -q", "ruff check .", "ls src/", "cat src/a.py", "grep -r foo src/",
                "git diff", "python3 -m pytest"):
        assert not _denied(_bash(tmp_path, cmd)), cmd


def test_bash_guard_allows_writes_to_non_source(tmp_path):
    _plan(tmp_path, "1")
    for cmd in ("echo hi > README.md", "echo '{}' > config.json", "echo x > notes.txt"):
        assert not _denied(_bash(tmp_path, cmd)), cmd


def test_bash_guard_inert_without_plan(tmp_path):
    (tmp_path / ".git").mkdir()
    assert not _denied(_bash(tmp_path, "echo x > src/a.py"))


def test_bash_guard_allows_out_of_tree_writes(tmp_path):
    # the plan governs project source, not arbitrary filesystem scratch
    _plan(tmp_path, "1")
    assert not _denied(_bash(tmp_path, "echo x > /tmp/up_scratch_file"))


def test_bash_guard_mirrors_scope_when_locked(tmp_path):
    _plan(tmp_path, "1")
    src = _mk(tmp_path, "src/a.py")
    _state(tmp_path, "lock", "--id", "1", "--file", str(src))
    # out-of-contract shell write denied (scope); in-contract test write allowed
    assert _denied(_bash(tmp_path, "echo x > src/other.py"))
    assert not _denied(_bash(tmp_path, "echo x > README.md"))


def test_bash_guard_fail_open_on_bad_stdin():
    out = subprocess.run([sys.executable, os.path.join(HOOKS, "bash-guard.py")],
                         input="not json", capture_output=True, text=True)
    assert out.returncode == 0


# --- impact-guard (ripple-into-scope) ----------------------------------------

def _fake_codegraph(project, affected=None, callers=None, query_files=None):
    """Install a PATH-shadowing `codegraph` whose JSON output is canned per subcommand.

    `query_files` maps a symbol name -> list of filePaths it is defined in; `codegraph query
    <S>` returns one definition node per file (used by the collision/uniqueness guard).
    It logs every invocation's argv to <bin>/calls.log so a test can assert `sync -q` ran.
    Returns (bin_dir, calls_log).
    """
    bin_dir = project / "bin"
    bin_dir.mkdir(exist_ok=True)
    calls_log = bin_dir / "calls.log"
    affected_json = json.dumps(affected or {"changedFiles": [], "affectedTests": [],
                                            "totalDependentsTraversed": 0})
    callers_json = json.dumps(callers or {"symbol": "", "callers": []})
    query_files = query_files or {}
    script = (project / "bin" / "codegraph")
    script.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys\n"
        f"open({str(calls_log)!r}, 'a').write(' '.join(sys.argv[1:]) + '\\n')\n"
        "cmd = sys.argv[1] if len(sys.argv) > 1 else ''\n"
        f"affected = {affected_json!r}\n"
        f"callers = {callers_json!r}\n"
        f"query_files = {json.dumps(query_files)!r}\n"
        "if cmd == 'affected':\n"
        "    print(affected)\n"
        "elif cmd == 'callers':\n"
        "    print(callers)\n"
        "elif cmd == 'query':\n"
        "    sym = sys.argv[2] if len(sys.argv) > 2 else ''\n"
        "    files = json.loads(query_files).get(sym, [])\n"
        "    print(json.dumps([{'node': {'name': sym, 'kind': 'function', 'filePath': f}}\n"
        "                      for f in files]))\n"
        "sys.exit(0)\n"
    )
    os.chmod(script, 0o755)
    (project / ".codegraph").mkdir(exist_ok=True)
    return bin_dir, calls_log


def _run_impact(project, data, bin_dir):
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])
    return subprocess.run(
        [sys.executable, os.path.join(HOOKS, "impact-guard.py")],
        input=json.dumps(data), capture_output=True, text=True, env=env,
    )


def test_impact_guard_runs_sync_at_root(tmp_path):
    bin_dir, calls_log = _fake_codegraph(tmp_path)
    (tmp_path / ".git").mkdir(exist_ok=True)
    out = _run_impact(tmp_path, _edit(tmp_path, _mk(tmp_path, "src/a.py")), bin_dir)
    assert out.returncode == 0 and out.stderr.strip() == ""
    assert "sync -q" in calls_log.read_text()


def test_impact_guard_blocks_on_affected_outside_contract(tmp_path):
    src = _mk(tmp_path, "src/a.py")
    bin_dir, _ = _fake_codegraph(tmp_path, affected={
        "changedFiles": ["src/a.py"],
        "affectedTests": [{"filePath": "tests/test_other.py"}],
        "totalDependentsTraversed": 1,
    })
    _lock(tmp_path, [src], red=True)
    out = _run_impact(tmp_path, _edit(tmp_path, src), bin_dir)
    assert out.returncode == 2
    assert "test_other.py" in out.stderr


def _edit_payload(project, path, new_string):
    return {"cwd": str(project), "tool_name": "Edit",
            "tool_input": {"file_path": str(path), "new_string": new_string}}


def test_impact_guard_blocks_on_caller_outside_contract(tmp_path):
    src = _mk(tmp_path, "src/a.py", "def foo():\n    return 1\n")
    # foo is defined in exactly one file -> uniqueness check passes -> block fires.
    bin_dir, _ = _fake_codegraph(tmp_path, callers={
        "symbol": "foo",
        "callers": [{"filePath": "src/consumer.py", "startLine": 3}],
    }, query_files={"foo": ["src/a.py"]})
    _lock(tmp_path, [src], red=True)
    out = _run_impact(tmp_path, _edit_payload(tmp_path, src, "def foo():\n    return 1\n"), bin_dir)
    assert out.returncode == 2
    assert "consumer.py" in out.stderr


def test_impact_guard_no_block_on_symbol_name_collision(tmp_path):
    src = _mk(tmp_path, "src/a.py", "def run():\n    return 1\n")
    # `run` is defined in TWO files -> callers cannot be attributed -> symbol is skipped,
    # so the out-of-contract caller never produces a (false) block.
    bin_dir, _ = _fake_codegraph(tmp_path, callers={
        "symbol": "run",
        "callers": [{"filePath": "src/b.py", "startLine": 3}],
    }, query_files={"run": ["src/a.py", "src/b.py"]})
    _lock(tmp_path, [src], red=True)
    out = _run_impact(tmp_path, _edit_payload(tmp_path, src, "def run():\n    return 1\n"), bin_dir)
    assert out.returncode == 0 and out.stderr.strip() == ""


def test_impact_guard_no_block_when_dependents_in_contract(tmp_path):
    src = _mk(tmp_path, "src/a.py", "def foo():\n    return 1\n")
    consumer = _mk(tmp_path, "src/consumer.py")
    bin_dir, _ = _fake_codegraph(tmp_path, callers={
        "symbol": "foo",
        "callers": [{"filePath": "src/consumer.py", "startLine": 3}],
    }, query_files={"foo": ["src/a.py"]})
    _lock(tmp_path, [src, consumer], red=True)
    out = _run_impact(tmp_path, _edit_payload(tmp_path, src, "def foo():\n    return 1\n"), bin_dir)
    assert out.returncode == 0 and out.stderr.strip() == ""


def test_impact_guard_fail_open_on_bad_stdin():
    out = subprocess.run([sys.executable, os.path.join(HOOKS, "impact-guard.py")],
                         input="not json", capture_output=True, text=True)
    assert out.returncode == 0
