#!/usr/bin/env python3
"""Shared state helpers for the ultrapower plugin's per-project `.scrum/` directory.

Layout under `<project>/.scrum/`:
  config.json         machine-read: verify commands, sprint length, Definition of Done
  current-story.json  machine-read: active story brief, locked file contract, red-test flag
  backlog.md          agent-authored: stories not yet in a sprint
  sprint.md           agent-authored: current sprint goal + committed stories
  velocity.md         agent-authored: points completed per past sprint
  retro.md            agent-authored: retrospective notes

Hooks and commands import this module to locate that directory and read/write the
JSON state. Kept dependency-free so the hooks run under a bare python3.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys

SCRUM_DIRNAME = ".scrum"

DEFAULT_CONFIG = {
    "sprint_length_days": 7,
    "scrum_visibility": "local",
    "verify": {"test": "", "lint": "", "typecheck": "", "smoke": ""},
    "definition_of_done": [
        "tests pass",
        "lint clean",
        "typecheck clean",
        "runtime smoke ok",
        "navigator review: no open blockers",
    ],
}

SCAFFOLD = {
    "backlog.md": "# Product Backlog\n\n| ID | Story | Points | Acceptance |\n|----|-------|--------|------------|\n",
    "sprint.md": "# Current Sprint\n\n_No active sprint. Run `/up:sprint plan`._\n",
    "velocity.md": "# Velocity\n\n| Sprint | Goal | Committed | Completed |\n|--------|------|-----------|-----------|\n",
    "retro.md": "# Retrospectives\n",
}


def find_project_root(start=None):
    """Walk up from `start` (default cwd) to the dir holding `.scrum/` or `.git/`.

    Returns the starting dir when no marker is found, so a fresh repo still has a
    stable root to initialise.
    """
    base = os.path.realpath(start or os.getcwd())
    d = base
    while True:
        if os.path.isdir(os.path.join(d, SCRUM_DIRNAME)) or os.path.isdir(os.path.join(d, ".git")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            return base
        d = parent


def scrum_dir(root):
    return os.path.join(root, SCRUM_DIRNAME)


def ensure_scrum(root):
    path = scrum_dir(root)
    os.makedirs(path, exist_ok=True)
    return path


def _read_json(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def config_path(root):
    return os.path.join(scrum_dir(root), "config.json")


def load_config(root):
    return _read_json(config_path(root), copy.deepcopy(DEFAULT_CONFIG))


def save_config(root, config):
    _write_json(config_path(root), config)


def get_visibility(root):
    return load_config(root).get("scrum_visibility", "local")


def set_visibility(root, mode):
    cfg = load_config(root)
    cfg["scrum_visibility"] = mode
    save_config(root, cfg)


def sync_gitignore(root):
    """Ensure .serena/ and .codegraph/ are always ignored; toggle .scrum/ per visibility."""
    gi_path = os.path.join(root, ".gitignore")
    try:
        with open(gi_path) as f:
            lines = f.read().splitlines(keepends=True)
    except OSError:
        lines = []

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    existing = {ln.rstrip("\n") for ln in lines}
    local = get_visibility(root) == "local"

    to_add = []
    for entry in (".serena/", ".codegraph/"):
        if entry not in existing:
            to_add.append(entry + "\n")

    scrum_entry = ".scrum/"
    has_scrum = scrum_entry in existing
    if local and not has_scrum:
        to_add.append(scrum_entry + "\n")

    if to_add:
        lines.extend(to_add)

    if not local and has_scrum:
        lines = [ln for ln in lines if ln.rstrip("\n") != scrum_entry]

    with open(gi_path, "w") as f:
        f.writelines(lines)


def current_story_path(root):
    return os.path.join(scrum_dir(root), "current-story.json")


def load_current_story(root):
    return _read_json(current_story_path(root), None)


def save_current_story(root, story):
    _write_json(current_story_path(root), story)


def clear_current_story(root):
    try:
        os.remove(current_story_path(root))
    except OSError:
        pass


def scaffold(root):
    """Create the agent-authored markdown files if absent; never overwrite."""
    ensure_scrum(root)
    for name, body in SCAFFOLD.items():
        path = os.path.join(scrum_dir(root), name)
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(body)


_MCP_DEPS = [
    ("codegraph", "claude mcp add codegraph -- codegraph serve --mcp"),
    ("serena", "claude mcp add serena -- serena start-mcp-server --context=claude-code --project-from-cwd"),
]


def check_dependencies(root):
    """Return a list of {name, kind, present} records for MCP and verify-tool deps."""
    cfg = load_config(root)
    verify = cfg.get("verify", {})

    seen = set()
    records = []

    for name, _ in _MCP_DEPS:
        records.append({"name": name, "kind": "mcp", "present": shutil.which(name) is not None})

    for cmd in verify.values():
        if not cmd or not cmd.strip():
            continue
        tool = cmd.strip().split()[0]
        if tool in seen:
            continue
        seen.add(tool)
        records.append({"name": tool, "kind": "verify", "present": shutil.which(tool) is not None})

    return records


_BOOTSTRAP = [
    ("codegraph", ".codegraph", lambda root: ["codegraph", "init", root]),
    ("serena", ".serena", lambda root: ["serena", "project", "create", root]),
]

_BOOTSTRAP_TIMEOUT = 120


def bootstrap_tools(root):
    """Run codegraph init and serena project create for the given project root.

    Success is the post-condition that the repo-local index dir (.codegraph/ or
    .serena/) exists afterward — NOT the command's exit code. This keeps both
    indexes repo-local and tolerates tools that exit non-zero when the project is
    already registered (e.g. `serena project create` on a re-init) as long as the
    local dir is present.

    Never raises; OSError/TimeoutExpired is captured in output.
    Returns a list of {"name", "ok", "present", "output"} records.
    """
    results = []
    for name, sentinel, argv_fn in _BOOTSTRAP:
        cmd = argv_fn(root)
        try:
            proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=_BOOTSTRAP_TIMEOUT)
            output = (proc.stdout + proc.stderr).strip()
        except (subprocess.TimeoutExpired, OSError) as exc:
            output = str(exc)
        present = os.path.isdir(os.path.join(root, sentinel))
        if not present:
            output = (output + f"\nexpected repo-local {sentinel}/ not found in {root}").strip()
        results.append({"name": name, "ok": present, "present": present, "output": output})
    return results


def _cli(argv=None):
    import argparse

    parser = argparse.ArgumentParser(prog="scrum_state")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--test", default="")
    p_init.add_argument("--lint", default="")
    p_init.add_argument("--typecheck", default="")
    p_init.add_argument("--smoke", default="")
    p_init.add_argument("--sprint-days", type=int, default=7)
    p_init.add_argument("--force", action="store_true")
    p_init.add_argument("--scrum-mode", choices=["local", "shared"], default="local")
    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--id", required=True)
    p_lock.add_argument("--title", default="")
    p_lock.add_argument("--points", type=int, default=0)
    p_lock.add_argument("--file", action="append", default=[], dest="files")
    p_lock.add_argument("--acceptance", action="append", default=[], dest="acceptance")
    p_lock.add_argument("--out", action="append", default=[], dest="out_of_scope")
    p_addfile = sub.add_parser("add-file")
    p_addfile.add_argument("--file", action="append", default=[], dest="files", required=True)
    sub.add_parser("mark-red")
    sub.add_parser("close")
    sub.add_parser("show")
    sub.add_parser("doctor")
    sub.add_parser("bootstrap")
    args = parser.parse_args(argv)

    root = find_project_root()
    if args.cmd == "lock":
        save_current_story(root, {
            "id": args.id,
            "title": args.title,
            "points": args.points,
            "files": [os.path.realpath(f if os.path.isabs(f) else os.path.join(root, f)) for f in args.files],
            "acceptance": args.acceptance,
            "out_of_scope": args.out_of_scope,
            "red_test_observed": False,
            "status": "in-progress",
            "findings": [],
        })
        print(current_story_path(root))
        return 0
    if args.cmd == "add-file":
        story = load_current_story(root) or {"files": []}
        story.setdefault("files", [])
        story["files"] = sorted(set(story["files"]) | {os.path.realpath(f if os.path.isabs(f) else os.path.join(root, f)) for f in args.files})
        save_current_story(root, story)
        print(current_story_path(root))
        return 0
    if args.cmd == "mark-red":
        story = load_current_story(root)
        if not story:
            print("no active story", file=sys.stderr)
            return 1
        story["red_test_observed"] = True
        save_current_story(root, story)
        print("red_test_observed=true")
        return 0
    if args.cmd == "close":
        clear_current_story(root)
        print("story closed")
        return 0
    if args.cmd == "show":
        if os.path.isfile(config_path(root)):
            print(json.dumps(load_config(root), indent=2))
        else:
            print("no .scrum/config.json (run /up:init)")
        return 0

    if args.cmd == "doctor":
        report = check_dependencies(root)
        mcp_guidance = {name: guidance for name, guidance in _MCP_DEPS}
        for rec in report:
            status = "OK" if rec["present"] else "MISSING"
            print(f"  [{status}] {rec['name']} ({rec['kind']})")
        missing_mcp = [r for r in report if r["kind"] == "mcp" and not r["present"]]
        if missing_mcp:
            print()
            print("To install missing MCP deps, run manually:")
            for rec in missing_mcp:
                print(f"  {mcp_guidance[rec['name']]}")
        return 0

    if args.cmd == "bootstrap":
        results = bootstrap_tools(root)
        for rec in results:
            status = "ok" if rec["ok"] else "FAIL"
            print(f"  {rec['name']:12} {status}")
            if not rec["ok"] and rec["output"]:
                print(f"    {rec['output'][:200]}")
        if all(r["ok"] for r in results):
            print("  repo-local .codegraph/ and .serena/ present")
        return 0

    if os.path.isfile(config_path(root)) and not args.force:
        print(json.dumps(load_config(root), indent=2))
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["sprint_length_days"] = args.sprint_days
    cfg["scrum_visibility"] = args.scrum_mode
    cfg["verify"] = {"test": args.test, "lint": args.lint, "typecheck": args.typecheck, "smoke": args.smoke}
    save_config(root, cfg)
    scaffold(root)
    sync_gitignore(root)
    print(config_path(root))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
