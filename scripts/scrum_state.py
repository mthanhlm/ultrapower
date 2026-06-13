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
import sys

SCRUM_DIRNAME = ".scrum"

DEFAULT_CONFIG = {
    "sprint_length_days": 7,
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
    args = parser.parse_args(argv)

    root = find_project_root()
    if args.cmd == "lock":
        save_current_story(root, {
            "id": args.id,
            "title": args.title,
            "points": args.points,
            "files": [os.path.realpath(f) for f in args.files],
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
        story["files"] = sorted(set(story["files"]) | {os.path.realpath(f) for f in args.files})
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

    if os.path.isfile(config_path(root)) and not args.force:
        print(json.dumps(load_config(root), indent=2))
        return 0
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    cfg["sprint_length_days"] = args.sprint_days
    cfg["verify"] = {"test": args.test, "lint": args.lint, "typecheck": args.typecheck, "smoke": args.smoke}
    save_config(root, cfg)
    scaffold(root)
    print(config_path(root))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
