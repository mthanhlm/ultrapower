import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP_MD = os.path.join(ROOT, "commands", "setup.md")


def _make_config(tmp_path, verify):
    scrum_state.save_config(str(tmp_path), {
        "verify": verify,
    })


def test_mcp_deps_always_present_in_report(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "", "lint": "", "typecheck": "", "smoke": ""})
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name if name == "codegraph" else None)
    report = scrum_state.check_dependencies(str(tmp_path))
    names = {r["name"]: r for r in report}
    assert "codegraph" in names
    assert "serena" in names
    assert names["codegraph"]["present"] is True
    assert names["serena"]["present"] is False
    assert names["codegraph"]["kind"] == "mcp"
    assert names["serena"]["kind"] == "mcp"


def test_verify_tools_probed_for_nonempty_entries(tmp_path, monkeypatch):
    _make_config(tmp_path, {
        "test": "pytest -q",
        "lint": "ruff check .",
        "typecheck": "",
        "smoke": "python3 scripts/scrum_state.py show",
    })
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name if name in {"pytest", "ruff"} else None)
    report = scrum_state.check_dependencies(str(tmp_path))
    verify_entries = {r["name"]: r for r in report if r["kind"] == "verify"}
    assert "pytest" in verify_entries
    assert "ruff" in verify_entries
    assert "python3" in verify_entries
    assert verify_entries["pytest"]["present"] is True
    assert verify_entries["ruff"]["present"] is True
    assert verify_entries["python3"]["present"] is False


def test_empty_verify_entries_skipped(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "pytest -q", "lint": "", "typecheck": "", "smoke": ""})
    monkeypatch.setattr("shutil.which", lambda name: None)
    report = scrum_state.check_dependencies(str(tmp_path))
    verify_names = [r["name"] for r in report if r["kind"] == "verify"]
    assert "pytest" in verify_names
    # lint/typecheck/smoke are empty — their slots must not appear
    assert len(verify_names) == 1


def test_first_token_extracted_from_verify_command(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "python3 -m pytest -q", "lint": "", "typecheck": "", "smoke": ""})
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    report = scrum_state.check_dependencies(str(tmp_path))
    verify_names = [r["name"] for r in report if r["kind"] == "verify"]
    assert "python3" in verify_names
    assert "pytest" not in verify_names


def test_report_deduplicates_same_tool(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "pytest -q", "lint": "pytest --lint", "typecheck": "", "smoke": ""})
    monkeypatch.setattr("shutil.which", lambda name: None)
    report = scrum_state.check_dependencies(str(tmp_path))
    verify_names = [r["name"] for r in report if r["kind"] == "verify"]
    assert verify_names.count("pytest") == 1


def test_setup_md_exists():
    assert os.path.isfile(SETUP_MD), f"commands/setup.md not found at {SETUP_MD}"


def test_setup_md_references_doctor_check():
    body = open(SETUP_MD).read()
    # Must reference the doctor subcommand invocation pattern
    assert re.search(r"scrum_state\.py.*doctor|doctor.*subcommand|doctor.*check", body, re.IGNORECASE), (
        "setup.md must reference the doctor check (scrum_state.py doctor or similar)"
    )


def test_setup_md_states_checks_only():
    body = open(SETUP_MD).read()
    # Must explicitly say it checks/guides only (never auto-installs)
    assert re.search(r"checks?\s+(and\s+guides?|only)|guides?\s+only|never\s+(auto.?install|install)", body, re.IGNORECASE), (
        "setup.md must state it checks/guides only and never auto-installs"
    )
