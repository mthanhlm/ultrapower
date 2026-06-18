import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402

SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "scrum_state.py")


def _run(args, cwd, check=True):
    r = subprocess.run([sys.executable, SCRIPT, *args], cwd=str(cwd), capture_output=True, text=True)
    if check:
        assert r.returncode == 0, r.stderr
    return r


# --- roots, config -----------------------------------------------------------

def test_find_project_root_uses_git_marker(tmp_path):
    (tmp_path / ".git").mkdir()
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert scrum_state.find_project_root(str(nested)) == os.path.realpath(str(tmp_path))


def test_config_defaults_when_missing(tmp_path):
    cfg = scrum_state.load_config(str(tmp_path))
    assert "scrum_visibility" not in cfg
    assert "definition_of_done" not in cfg
    assert "test" in cfg["verify"]


def test_loaded_config_does_not_leak_into_default(tmp_path):
    cfg = scrum_state.load_config(str(tmp_path))
    cfg["verify"]["test"] = "pytest -q"
    scrum_state.save_config(str(tmp_path), cfg)
    assert scrum_state.load_config(str(tmp_path))["verify"]["test"] == "pytest -q"
    assert scrum_state.DEFAULT_CONFIG["verify"]["test"] == ""


def test_cli_init_writes_config_and_gitignores_scrum(tmp_path):
    (tmp_path / ".git").mkdir()
    r = _run(["init", "--test", "pytest -q"], tmp_path)
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["verify"]["test"] == "pytest -q"
    assert "scrum_visibility" not in cfg
    assert ".scrum/" in (tmp_path / ".gitignore").read_text()
    assert r.returncode == 0


def test_cli_init_preserves_existing_without_force(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["init", "--test", "first"], tmp_path)
    _run(["init", "--test", "second"], tmp_path)
    cfg = json.loads((tmp_path / ".scrum" / "config.json").read_text())
    assert cfg["verify"]["test"] == "first"


# --- the active locked step --------------------------------------------------

def test_current_story_round_trip(tmp_path):
    assert scrum_state.load_current_story(str(tmp_path)) is None
    scrum_state.save_current_story(str(tmp_path), {"id": "1", "files": ["/x/a.py"]})
    assert scrum_state.load_current_story(str(tmp_path))["id"] == "1"
    scrum_state.clear_current_story(str(tmp_path))
    assert scrum_state.load_current_story(str(tmp_path)) is None


def test_cli_lock_writes_current_story(tmp_path):
    (tmp_path / ".git").mkdir()
    src = tmp_path / "a.py"
    src.write_text("x = 1\n")
    _run(["lock", "--id", "3", "--title", "do a thing", "--points", "3",
          "--file", str(src), "--acceptance", "it works"], tmp_path)
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    assert story["id"] == "3"
    assert story["red_criteria"] == []
    assert story["status"] == "in-progress"
    assert story["files"] == [os.path.realpath(str(src))]


def test_cli_lock_root_anchors_relative_file_from_subdir(tmp_path):
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    _run(["lock", "--id", "9", "--file", "tests/foo.py", "--acceptance", "path anchored"], subdir)
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    assert story["files"] == [os.path.realpath(str(tmp_path / "tests" / "foo.py"))]


def test_cli_add_file_extends_contract_anchored_to_root(tmp_path):
    (tmp_path / ".git").mkdir()
    subdir = tmp_path / "sub"
    subdir.mkdir()
    _run(["lock", "--id", "1", "--file", "a.py"], subdir)
    _run(["add-file", "--file", "b.py"], subdir)
    story = json.loads((tmp_path / ".scrum" / "current-story.json").read_text())
    assert os.path.realpath(str(tmp_path / "b.py")) in story["files"]


def test_cli_close_clears_current_story(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    _run(["lock", "--id", "1", "--file", str(tmp_path / "a.py")], tmp_path)
    _run(["close"], tmp_path)
    assert not (tmp_path / ".scrum" / "current-story.json").exists()


# --- per-criterion TDD latch -------------------------------------------------

def test_red_unlocked_reads_per_criterion(tmp_path):
    assert scrum_state.red_unlocked(None) is False
    assert scrum_state.red_unlocked({"red_criteria": []}) is False
    assert scrum_state.red_unlocked({"red_criteria": ["c1"]}) is True


def test_criteria_covered_is_identity_based_not_count():
    ok, missing = scrum_state.criteria_covered({"acceptance": ["a", "b"], "red_criteria": ["a"]})
    assert ok is False and missing == 1
    ok, missing = scrum_state.criteria_covered({"acceptance": ["a", "b"], "red_criteria": ["a", "b"]})
    assert ok is True and missing == 0
    # junk reds must NOT count toward coverage even if they outnumber the criteria
    ok, missing = scrum_state.criteria_covered({"acceptance": ["a", "b"], "red_criteria": ["x", "y", "z"]})
    assert ok is False and missing == 2
    ok, _ = scrum_state.criteria_covered({"acceptance": [], "red_criteria": []})
    assert ok is True  # refactor / no criteria


def test_is_code_file_inverts_to_non_code_denylist():
    # unlisted languages and extensionless source default to code (governed); docs/config do not.
    for code in ("a.py", "a.ex", "a.lua", "a.dart", "a.clj", "Dockerfile", "Makefile", "run"):
        assert scrum_state.is_code_file(code) is True, code
    for noncode in ("README.md", "config.yaml", "data.json", "x.toml", "LICENSE", "pic.png"):
        assert scrum_state.is_code_file(noncode) is False, noncode


def test_cli_mark_red_and_check_tdd_gate(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    _run(["lock", "--id", "1", "--file", str(tmp_path / "a.py"),
          "--acceptance", "rejects empty", "--acceptance", "rejects spaces"], tmp_path)
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 1  # 0 reds, 2 criteria
    _run(["mark-red", "--criterion", "rejects empty"], tmp_path)
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 1  # 1 red, still short
    _run(["mark-red", "--criterion", "rejects spaces"], tmp_path)
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 0  # covered


def test_cli_check_tdd_passes_for_refactor_without_red(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    _run(["lock", "--id", "1", "--file", str(tmp_path / "a.py"), "--kind", "refactor"], tmp_path)
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 0


def test_cli_check_tdd_fails_when_nonrefactor_has_no_acceptance(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    _run(["lock", "--id", "1", "--file", str(tmp_path / "a.py")], tmp_path)  # no acceptance, story kind
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 1


def test_cli_mark_red_rejects_unmatched_criterion(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    _run(["lock", "--id", "1", "--file", str(tmp_path / "a.py"),
          "--acceptance", "rejects empty", "--acceptance", "rejects spaces"], tmp_path)
    # bare mark-red and junk labels are refused — can't be used to inflate the count
    assert _run(["mark-red"], tmp_path, check=False).returncode == 1
    assert _run(["mark-red", "--criterion", "garbage"], tmp_path, check=False).returncode == 1
    assert scrum_state.load_current_story(str(tmp_path))["red_criteria"] == []


def test_blind_mark_red_cannot_game_check_tdd(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "a.py").write_text("x = 1\n")
    _run(["lock", "--id", "1", "--file", str(tmp_path / "a.py"),
          "--acceptance", "c one", "--acceptance", "c two"], tmp_path)
    for _ in range(5):  # five blind attempts must NOT satisfy a 2-criterion gate
        _run(["mark-red"], tmp_path, check=False)
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 1
    _run(["mark-red", "--criterion", "C ONE"], tmp_path)   # case/space-insensitive match
    _run(["mark-red", "--criterion", "c two"], tmp_path)
    assert _run(["check-tdd"], tmp_path, check=False).returncode == 0


def test_cli_lock_rejects_id_not_in_plan(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    r = _run(["lock", "--id", "99", "--file", "a.py"], tmp_path, check=False)
    assert r.returncode == 1 and "not in the plan" in r.stderr
    assert scrum_state.load_current_story(str(tmp_path)) is None  # no phantom lock written


def test_cli_lock_rejects_refactor_with_acceptance(tmp_path):
    (tmp_path / ".git").mkdir()
    r = _run(["lock", "--id", "1", "--file", "a.py", "--kind", "refactor",
              "--acceptance", "new behaviour"], tmp_path, check=False)
    assert r.returncode == 1
    assert scrum_state.load_current_story(str(tmp_path)) is None


def test_cli_lock_rejects_oversized_file_contract(tmp_path):
    (tmp_path / ".git").mkdir()
    files = []
    for i in range(7):  # > MAX_CONTRACT_FILES (6)
        files += ["--file", f"f{i}.py"]
    r = _run(["lock", "--id", "1", *files], tmp_path, check=False)
    assert r.returncode == 1 and "files" in r.stderr
    assert scrum_state.load_current_story(str(tmp_path)) is None


def test_cli_lock_allows_oversized_when_plan_step_marked(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "big", "--oversized", "atomic migration"], tmp_path)
    files = []
    for i in range(8):
        files += ["--file", f"f{i}.py"]
    assert _run(["lock", "--id", "1", *files], tmp_path, check=False).returncode == 0


def test_cli_close_marks_step_done(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["plan-add", "--id", "2", "--title", "b"], tmp_path)
    _run(["lock", "--id", "1", "--file", "a.py"], tmp_path)
    _run(["close"], tmp_path)  # close alone must mark done — no separate step-status needed
    assert scrum_state.get_step(str(tmp_path), "1")["status"] == "done"
    assert scrum_state.next_todo_step(str(tmp_path))["id"] == "2"


def test_cli_plan_step_emits_full_contract(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "v", "--points", "2",
          "--file", "v.py", "--acceptance", "c1", "--out", "no DNS", "--kind", "story"], tmp_path)
    out = _run(["plan-step", "--id", "1"], tmp_path)
    step = json.loads(out.stdout)
    assert step["acceptance"] == ["c1"] and step["out_of_scope"] == ["no DNS"]
    assert step["points"] == 2 and step["kind"] == "story"
    assert step["files"][0].endswith("v.py")


def test_plan_add_dedups_normalizing_id_type(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "first"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "rewritten"], tmp_path)
    steps = scrum_state.load_plan(str(tmp_path))["steps"]
    assert len(steps) == 1 and steps[0]["title"] == "rewritten"


def test_status_footer_lists_blocked_steps(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["lock", "--id", "1", "--file", "a.py"], tmp_path)
    _run(["abort"], tmp_path)
    out = _run(["status"], tmp_path).stdout
    assert "blocked" in out.lower() and "/up:run" in out


# --- the plan ----------------------------------------------------------------

def test_plan_new_add_and_load(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "reject malformed emails"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "validator", "--points", "2",
          "--file", "v.py", "--acceptance", "c1", "--acceptance", "c2"], tmp_path)
    _run(["plan-add", "--id", "2", "--title", "wire it", "--points", "1"], tmp_path)
    plan = scrum_state.load_plan(str(tmp_path))
    assert plan["task"] == "reject malformed emails"
    assert [s["id"] for s in plan["steps"]] == ["1", "2"]
    assert plan["steps"][0]["acceptance"] == ["c1", "c2"]
    assert plan["steps"][0]["files"] == [os.path.realpath(str(tmp_path / "v.py"))]


def test_plan_add_is_idempotent_by_id(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "first"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "rewritten"], tmp_path)
    plan = scrum_state.load_plan(str(tmp_path))
    assert len(plan["steps"]) == 1 and plan["steps"][0]["title"] == "rewritten"


def test_next_todo_and_step_status_flow(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["plan-add", "--id", "2", "--title", "b"], tmp_path)
    assert scrum_state.next_todo_step(str(tmp_path))["id"] == "1"
    assert scrum_state.has_unfinished_plan(str(tmp_path)) is True
    _run(["step-status", "--id", "1", "--status", "done"], tmp_path)
    assert scrum_state.next_todo_step(str(tmp_path))["id"] == "2"
    _run(["step-status", "--id", "2", "--status", "done"], tmp_path)
    assert scrum_state.next_todo_step(str(tmp_path)) is None
    assert scrum_state.has_unfinished_plan(str(tmp_path)) is False


def test_aborted_step_does_not_block_plan_completion(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["step-status", "--id", "1", "--status", "aborted"], tmp_path)
    assert scrum_state.has_unfinished_plan(str(tmp_path)) is False


def test_blocked_step_is_skipped_by_run_loop(tmp_path):
    # An aborted (-> blocked) step is not auto-retried by /up:run all; the loop advances past it.
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["plan-add", "--id", "2", "--title", "b"], tmp_path)
    _run(["lock", "--id", "1", "--file", "a.py"], tmp_path)
    _run(["abort"], tmp_path)  # step 1 -> blocked, lock released
    assert scrum_state.next_todo_step(str(tmp_path))["id"] == "2"
    _run(["step-status", "--id", "2", "--status", "done"], tmp_path)
    # only a blocked step remains -> nothing drivable -> plan-guard goes inert
    assert scrum_state.has_unfinished_plan(str(tmp_path)) is False


def test_cli_lock_marks_step_current(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["lock", "--id", "1", "--file", "a.py"], tmp_path)
    plan = scrum_state.load_plan(str(tmp_path))
    assert plan["steps"][0]["status"] == "current"


def test_cli_plan_next_prints_id(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "7", "--title", "a"], tmp_path)
    out = _run(["plan-next"], tmp_path)
    assert out.stdout.strip() == "7"


def test_cli_abort_releases_lock_and_marks_blocked(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "a"], tmp_path)
    _run(["lock", "--id", "1", "--file", "a.py"], tmp_path)
    _run(["abort"], tmp_path)
    assert scrum_state.load_current_story(str(tmp_path)) is None
    assert scrum_state.get_step(str(tmp_path), "1")["status"] == "blocked"


def test_render_plan_shows_statuses(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "ship X"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "step one", "--points", "2"], tmp_path)
    _run(["step-status", "--id", "1", "--status", "done"], tmp_path)
    rendered = scrum_state.render_plan(str(tmp_path))
    assert "ship X" in rendered
    assert "[x] 1. step one" in rendered


def test_render_plan_flags_oversized(tmp_path):
    (tmp_path / ".git").mkdir()
    _run(["plan-new", "--task", "t"], tmp_path)
    _run(["plan-add", "--id", "1", "--title", "big", "--points", "5",
          "--oversized", "split refused: atomic migration"], tmp_path)
    assert "oversized" in scrum_state.render_plan(str(tmp_path))


# --- gitignore, ladder, lean-debt, doctor ------------------------------------

def test_sync_gitignore_ignores_state_dirs_idempotently(tmp_path):
    scrum_state.sync_gitignore(str(tmp_path))
    body = (tmp_path / ".gitignore").read_text()
    for entry in (".scrum/", ".serena/", ".codegraph/"):
        assert entry in body
    scrum_state.sync_gitignore(str(tmp_path))
    assert (tmp_path / ".gitignore").read_text().count(".scrum/") == 1


def test_ladder_text_returns_body():
    assert "Does this need to exist" in scrum_state.ladder_text()


def test_ladder_file_exists_and_has_rungs():
    assert os.path.isfile(scrum_state._LADDER_PATH)
    body = open(scrum_state._LADDER_PATH).read()
    for rung in ("Stdlib does it", "one line", "minimum code that works"):
        assert rung in body


def test_lean_debt_parses_marker(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("x = 1  # lean: global lock, per-account if hot\n")
    row = scrum_state.scan_lean_debt(str(tmp_path), [str(f)])[0]
    assert row["file"] == "m.py" and row["line"] == 1
    assert row["ceiling"] == "global lock" and row["upgrade"] == "per-account if hot"
    assert row["no_trigger"] is False


def test_lean_debt_flags_no_trigger(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("# lean: naive O(n^2) scan\nx = 1\n")
    row = scrum_state.scan_lean_debt(str(tmp_path), [str(f)])[0]
    assert row["ceiling"] == "naive O(n^2) scan" and row["no_trigger"] is True


def test_lean_debt_empty_when_no_markers(tmp_path):
    f = tmp_path / "m.py"
    f.write_text("x = 1\n# just a normal comment\n")
    assert scrum_state.scan_lean_debt(str(tmp_path), [str(f)]) == []


def test_scan_lean_debt_whole_repo_via_git(tmp_path):
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True, text=True)
    (tmp_path / "a.py").write_text("# lean: stub, fix when X lands\nx = 1\n")
    subprocess.run(["git", "add", "."], cwd=str(tmp_path), capture_output=True, text=True)
    assert any(r["file"] == "a.py" for r in scrum_state.scan_lean_debt(str(tmp_path)))


def test_cli_lean_debt(tmp_path):
    (tmp_path / ".git").mkdir()
    (tmp_path / "m.py").write_text("# lean: stub, real impl when needed\nx = 1\n")
    _run(["init", "--force"], tmp_path)
    out = _run(["lean-debt", "--file", "m.py"], tmp_path)
    assert "m.py" in out.stdout and "1 marker" in out.stdout


def test_doctor_probes_mcp_registration_not_path(tmp_path, monkeypatch):
    (tmp_path / ".git").mkdir()
    monkeypatch.setattr(scrum_state, "registered_mcp_servers", lambda: {"codegraph"})
    monkeypatch.setattr(scrum_state, "find_project_root", lambda *a, **k: str(tmp_path))
    report = scrum_state.check_dependencies(str(tmp_path))
    by_name = {r["name"]: r for r in report}
    assert by_name["codegraph"]["present"] is True
    assert by_name["serena"]["present"] is False
