import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import scrum_state  # noqa: E402


def _make_config(tmp_path, verify):
    scrum_state.save_config(str(tmp_path), {"verify": verify})


def test_mcp_deps_probed_by_registration_not_path(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "", "lint": "", "typecheck": "", "smoke": ""})
    # A bare PATH check gives a false all-clear; the doctor must probe `claude mcp list`.
    monkeypatch.setattr(scrum_state, "registered_mcp_servers", lambda: {"codegraph"})
    names = {r["name"]: r for r in scrum_state.check_dependencies(str(tmp_path))}
    assert names["codegraph"]["present"] is True and names["codegraph"]["kind"] == "mcp"
    assert names["serena"]["present"] is False and names["serena"]["kind"] == "mcp"


def test_verify_tools_probed_for_nonempty_entries(tmp_path, monkeypatch):
    _make_config(tmp_path, {
        "test": "pytest -q", "lint": "ruff check .", "typecheck": "",
        "smoke": "python3 scripts/scrum_state.py show",
    })
    monkeypatch.setattr(scrum_state, "registered_mcp_servers", set)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name if name in {"pytest", "ruff"} else None)
    verify = {r["name"]: r for r in scrum_state.check_dependencies(str(tmp_path)) if r["kind"] == "verify"}
    assert verify["pytest"]["present"] is True
    assert verify["ruff"]["present"] is True
    assert verify["python3"]["present"] is False


def test_empty_verify_entries_skipped(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "pytest -q", "lint": "", "typecheck": "", "smoke": ""})
    monkeypatch.setattr(scrum_state, "registered_mcp_servers", set)
    monkeypatch.setattr("shutil.which", lambda name: None)
    verify_names = [r["name"] for r in scrum_state.check_dependencies(str(tmp_path)) if r["kind"] == "verify"]
    assert verify_names == ["pytest"]


def test_first_token_extracted_from_verify_command(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "python3 -m pytest -q", "lint": "", "typecheck": "", "smoke": ""})
    monkeypatch.setattr(scrum_state, "registered_mcp_servers", set)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/" + name)
    verify_names = [r["name"] for r in scrum_state.check_dependencies(str(tmp_path)) if r["kind"] == "verify"]
    assert "python3" in verify_names and "pytest" not in verify_names


def test_report_deduplicates_same_tool(tmp_path, monkeypatch):
    _make_config(tmp_path, {"test": "pytest -q", "lint": "pytest --lint", "typecheck": "", "smoke": ""})
    monkeypatch.setattr(scrum_state, "registered_mcp_servers", set)
    monkeypatch.setattr("shutil.which", lambda name: None)
    verify_names = [r["name"] for r in scrum_state.check_dependencies(str(tmp_path)) if r["kind"] == "verify"]
    assert verify_names.count("pytest") == 1


def test_registered_mcp_servers_empty_without_claude(monkeypatch):
    # No `claude` binary -> empty set (never a false all-clear).
    monkeypatch.setattr("subprocess.run", lambda *a, **k: (_ for _ in ()).throw(OSError()))
    assert scrum_state.registered_mcp_servers() == set()
