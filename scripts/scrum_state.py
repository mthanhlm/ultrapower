#!/usr/bin/env python3
"""Shared state helpers for the ultrapower plugin's per-project `.scrum/` directory.

Layout under `<project>/.scrum/`:
  config.json         machine-read: verify commands (test/lint/typecheck/smoke)
  plan.json           machine-read: the ordered list of small steps for the current task
  current-story.json  machine-read: the active locked step (file contract, per-criterion red set)

Hooks and commands import this module to locate that directory and read/write the
JSON state. Kept dependency-free so the hooks run under a bare python3.

The plan is stored as JSON (not a markdown table) on purpose: it removes the whole
fragile-table-parsing failure class and lets the renderer present it any way it likes.
"""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import subprocess
import sys

SCRUM_DIRNAME = ".scrum"

# A step is drivable by `/up:run all` only in these states; done/aborted/blocked are skipped, so a
# wedged (aborted -> blocked) step is never auto-retried and doesn't keep plan-guard armed forever.
# `/up:run <id>` can still re-drive a blocked step explicitly.
DRIVABLE_STATES = {"todo", "current"}

# Hard ceiling on a step's file contract — the machine floor that makes "small" a fact, not a
# heuristic. A step needing more must be split, or its plan step marked `oversized` (a conscious
# human/planner override that also makes /up:run pause at it).
MAX_CONTRACT_FILES = 6

DEFAULT_CONFIG = {
    "verify": {"test": "", "lint": "", "typecheck": "", "smoke": ""},
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
    """Write JSON atomically (temp + os.replace) so a crash never leaves a half-file."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def config_path(root):
    return os.path.join(scrum_dir(root), "config.json")


def load_config(root):
    return _read_json(config_path(root), copy.deepcopy(DEFAULT_CONFIG))


def save_config(root, config):
    _write_json(config_path(root), config)


def _abspaths(root, files):
    return [os.path.realpath(f if os.path.isabs(f) else os.path.join(root, f)) for f in files]


# Shared file classification — the hooks (plan/tdd/bash guards) agree on what counts as editable
# "source" vs a test. A non-code DENY-list is harder to bypass than a code allow-list: an unlisted
# language or an extensionless source file (Dockerfile, Makefile, a shebang script) defaults to
# code, so it is governed by the guards rather than slipping through.
NON_CODE_EXTS = {
    ".md", ".markdown", ".rst", ".txt", ".json", ".jsonc", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".conf", ".properties", ".lock", ".csv", ".tsv", ".xml", ".svg", ".png", ".jpg",
    ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".log", ".env", ".gitignore", ".gitattributes",
    ".editorconfig",
}
_NON_CODE_BASENAMES = {"license", "license.txt", "notice", "copying", "authors"}

_TEST_PATH = re.compile(
    r"(^|/)(tests?|__tests__|spec)(/|$)|(^|/)test_[^/]+$|[^/]+_test\.[a-z]+$|[^/]+\.(test|spec)\.[a-z]+$",
    re.I,
)


def is_test_file(path):
    return bool(_TEST_PATH.search(path.replace(os.sep, "/")))


def is_code_file(path):
    base = os.path.basename(path)
    if base.lower() in _NON_CODE_BASENAMES:
        return False
    return os.path.splitext(path)[1].lower() not in NON_CODE_EXTS


_LADDER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lean", "ladder.md")


def ladder_text(path=_LADDER_PATH):
    """The lean ladder, injected verbatim every session. Empty when the file is unreadable."""
    try:
        with open(path) as f:
            return f.read()
    except (OSError, ValueError):
        return ""


# lean: line grep, not a per-language parser — can match lean: inside string literals; parse per-language if the noise bites
_LEAN_DEBT = re.compile(r"(?:#|//|/\*+|--|;)\s*lean:\s*(.+?)\s*(?:\*/)?\s*$", re.I)


def _repo_files(root):
    try:
        out = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"],
                             cwd=root, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return []
    return [os.path.join(root, p) for p in out.stdout.splitlines() if p] if out.returncode == 0 else []


def scan_lean_debt(root, files=None):
    """Harvest `lean:` markers into a ledger. `files=None` scans the whole repo (git-tracked
    files); otherwise scans the given paths. Convention is `lean: <ceiling>, <upgrade path>` —
    a marker naming no upgrade path (no comma) is flagged `no_trigger`, the rot risk."""
    paths = files if files is not None else _repo_files(root)
    ledger = []
    for path in paths:
        try:
            with open(path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except (OSError, ValueError):
            continue
        for n, line in enumerate(lines, 1):
            m = _LEAN_DEBT.search(line)
            if not m:
                continue
            ceiling, _, upgrade = m.group(1).strip().partition(",")
            ledger.append({
                "file": os.path.relpath(path, root),
                "line": n,
                "ceiling": ceiling.strip(),
                "upgrade": upgrade.strip(),
                "no_trigger": not upgrade.strip(),
            })
    return ledger


def sync_gitignore(root):
    """Ensure ultrapower's machine-state dirs are always gitignored. `.scrum/` is local by
    design (per-developer working state, not team artifacts), alongside the .codegraph
    index. Idempotent: only appends missing entries."""
    gi_path = os.path.join(root, ".gitignore")
    try:
        with open(gi_path) as f:
            lines = f.read().splitlines(keepends=True)
    except OSError:
        lines = []

    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"

    existing = {ln.rstrip("\n") for ln in lines}
    to_add = [e + "\n" for e in (".scrum/", ".codegraph/") if e not in existing]
    if to_add:
        lines.extend(to_add)
        with open(gi_path, "w") as f:
            f.writelines(lines)


# --- the active locked step --------------------------------------------------

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


def red_unlocked(story):
    """Has the TDD gate opened — has at least one failing test been observed for this step?"""
    return bool(story and story.get("red_criteria"))


def _norm(s):
    return " ".join(s.lower().split())


def criteria_covered(story):
    """Per-criterion TDD floor: every acceptance criterion must have a recorded red test before a
    step may close. Identity-based — a recorded red counts only if it matches an acceptance
    criterion (mark-red enforces the match), so blind/junk reds can't satisfy the gate. A step
    with no acceptance criteria (a refactor) is ok."""
    acceptance = story.get("acceptance") or []
    if not acceptance:
        return True, 0
    reds = set(story.get("red_criteria") or [])
    covered = sum(1 for c in acceptance if c in reds)
    return covered >= len(acceptance), len(acceptance) - covered


def would_block_edit(root, target):
    """The reason an Edit to `target` (realpath) would be denied by the plan/scope/tdd guards, or
    None. Mirrors those three hooks so bash-guard can block a shell write that the edit guards
    would have blocked — keeping 'no source outside a locked step' true across tools."""
    if target.startswith(scrum_dir(root) + os.sep):
        return None
    # The plan governs THIS project's source — a write outside the repo root (e.g. /tmp scratch) is
    # out of scope, not a bypass. scope-guard separately confines a locked step to its contract.
    if target != root and not target.startswith(root + os.sep):
        return None
    story = load_current_story(root)
    if not story:
        if has_unfinished_plan(root) and is_code_file(target) and not is_test_file(target):
            return ("an unfinished plan exists but no step is locked — write source through "
                    "/up:run, not around it (or /up:status abort to clear the plan)")
        return None
    if target not in set(story.get("files", [])):
        return f"{os.path.basename(target)} is outside the locked contract for step '{story.get('id', '?')}'"
    if story.get("kind") != "refactor" and not red_unlocked(story) and not is_test_file(target):
        return f"TDD: no failing test observed yet for step '{story.get('id', '?')}' — write the test first"
    return None


# --- the plan ----------------------------------------------------------------

def plan_path(root):
    return os.path.join(scrum_dir(root), "plan.json")


def load_plan(root):
    return _read_json(plan_path(root), None)


def save_plan(root, plan):
    _write_json(plan_path(root), plan)


def clear_plan(root):
    try:
        os.remove(plan_path(root))
    except OSError:
        pass


def plan_new(root, task):
    save_plan(root, {"task": task, "steps": []})


def plan_add(root, step):
    plan = load_plan(root) or {"task": "", "steps": []}
    plan["steps"] = [s for s in plan["steps"] if str(s.get("id")) != str(step["id"])]
    plan["steps"].append(step)
    save_plan(root, plan)


def set_step_status(root, step_id, status):
    """Flip one step's status by id. Idempotent; False if the id is absent."""
    plan = load_plan(root)
    if not plan:
        return False
    found = False
    for s in plan["steps"]:
        if str(s.get("id")) == str(step_id):
            s["status"] = status
            found = True
    if found:
        save_plan(root, plan)
    return found


def next_todo_step(root):
    """The first step still owing work, in plan order. None when the plan is complete/empty."""
    plan = load_plan(root)
    if not plan:
        return None
    for s in plan["steps"]:
        if s.get("status", "todo") in DRIVABLE_STATES:
            return s
    return None


def has_unfinished_plan(root):
    return next_todo_step(root) is not None


def blocked_steps(root):
    plan = load_plan(root)
    return [s for s in (plan or {}).get("steps", []) if s.get("status") == "blocked"]


def get_step(root, step_id):
    plan = load_plan(root)
    if not plan:
        return None
    return next((s for s in plan["steps"] if str(s.get("id")) == str(step_id)), None)


def render_plan(root):
    """Human-readable view of plan.json for /up:status — the plan is stored as JSON, shown as text."""
    plan = load_plan(root)
    if not plan or not plan.get("steps"):
        return "No active plan. Run /up:plan <task>."
    mark = {"done": "[x]", "current": "[~]", "blocked": "[!]", "aborted": "[-]"}
    out = [f"Task: {plan.get('task', '')}", ""]
    for s in plan["steps"]:
        status = s.get("status", "todo")
        box = mark.get(status, "[ ]")
        tags = ""
        if s.get("kind") == "refactor":
            tags += "  (refactor)"
        if s.get("oversized"):
            tags += "  ⚠ oversized"
        out.append(f"{box} {s['id']}. {s.get('title', '')} ({s.get('points', '?')}pt, {status}){tags}")
    return "\n".join(out)


# --- dependency doctor + bootstrap -------------------------------------------

_MCP_DEPS = [
    ("codegraph", "claude mcp add codegraph -- codegraph serve --mcp"),
]


def registered_mcp_servers():
    """Server names registered with Claude Code, via `claude mcp list`. A bare PATH check
    (shutil.which) gives a false all-clear — a binary on PATH is not a server wired into
    Claude Code — so probe the real registration. Empty set if `claude` is unavailable."""
    try:
        out = subprocess.run(["claude", "mcp", "list"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return set()
    names = set()
    for line in out.stdout.splitlines():
        # `claude mcp list` prints "<name>: <command> - <status>" rows; take the leading token.
        m = re.match(r"\s*([A-Za-z0-9_-]+)\s*:", line)
        if m:
            names.add(m.group(1))
    return names


def check_dependencies(root):
    """Return a list of {name, kind, present} records for MCP and verify-tool deps."""
    verify = load_config(root).get("verify", {})
    registered = registered_mcp_servers()
    seen = set()
    records = [{"name": name, "kind": "mcp", "present": name in registered} for name, _ in _MCP_DEPS]
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
]

_BOOTSTRAP_TIMEOUT = 120


def bootstrap_tools(root):
    """Run codegraph init for the given project root.

    Success is the post-condition that the repo-local index dir (.codegraph/)
    exists afterward — NOT the command's exit code — so a tool that exits non-zero on a
    re-init still counts when its dir is present. Never raises.
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


# --- CLI ---------------------------------------------------------------------

def build_parser():
    import argparse

    parser = argparse.ArgumentParser(prog="scrum_state")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--test", default="")
    p_init.add_argument("--lint", default="")
    p_init.add_argument("--typecheck", default="")
    p_init.add_argument("--smoke", default="")
    p_init.add_argument("--force", action="store_true")

    p_pnew = sub.add_parser("plan-new")
    p_pnew.add_argument("--task", required=True)

    p_padd = sub.add_parser("plan-add")
    p_padd.add_argument("--id", required=True)
    p_padd.add_argument("--title", default="")
    p_padd.add_argument("--points", type=int, default=0)
    p_padd.add_argument("--file", action="append", default=[], dest="files")
    p_padd.add_argument("--acceptance", action="append", default=[], dest="acceptance")
    p_padd.add_argument("--out", action="append", default=[], dest="out_of_scope")
    p_padd.add_argument("--kind", default="story", choices=["story", "refactor"])
    p_padd.add_argument("--oversized", default="")

    sub.add_parser("plan-show")
    sub.add_parser("plan-next")
    p_pstep = sub.add_parser("plan-step")
    p_pstep.add_argument("--id", required=True)

    p_sstat = sub.add_parser("step-status")
    p_sstat.add_argument("--id", required=True)
    p_sstat.add_argument("--status", required=True,
                         choices=["todo", "current", "done", "blocked", "aborted"])

    p_lock = sub.add_parser("lock")
    p_lock.add_argument("--id", required=True)
    p_lock.add_argument("--title", default="")
    p_lock.add_argument("--points", type=int, default=0)
    p_lock.add_argument("--file", action="append", default=[], dest="files")
    p_lock.add_argument("--acceptance", action="append", default=[], dest="acceptance")
    p_lock.add_argument("--out", action="append", default=[], dest="out_of_scope")
    p_lock.add_argument("--kind", default="story", choices=["story", "refactor"])

    p_addfile = sub.add_parser("add-file")
    p_addfile.add_argument("--file", action="append", default=[], dest="files", required=True)

    p_red = sub.add_parser("mark-red")
    p_red.add_argument("--criterion", default="")

    sub.add_parser("check-tdd")

    p_debt = sub.add_parser("lean-debt")
    p_debt.add_argument("--file", action="append", default=None, dest="files")

    sub.add_parser("close")
    sub.add_parser("status")
    sub.add_parser("abort")
    sub.add_parser("show")
    sub.add_parser("doctor")
    sub.add_parser("bootstrap")
    return parser


def _cli(argv=None):
    args = build_parser().parse_args(argv)
    root = find_project_root()

    if args.cmd == "init":
        if os.path.isfile(config_path(root)) and not args.force:
            print(json.dumps(load_config(root), indent=2))
            return 0
        cfg = copy.deepcopy(DEFAULT_CONFIG)
        cfg["verify"] = {"test": args.test, "lint": args.lint, "typecheck": args.typecheck, "smoke": args.smoke}
        ensure_scrum(root)
        save_config(root, cfg)
        sync_gitignore(root)
        print(config_path(root))
        return 0

    if args.cmd == "plan-new":
        plan_new(root, args.task)
        print(plan_path(root))
        return 0

    if args.cmd == "plan-add":
        plan_add(root, {
            "id": args.id,
            "title": args.title,
            "points": args.points,
            "status": "todo",
            "files": _abspaths(root, args.files),
            "acceptance": args.acceptance,
            "out_of_scope": args.out_of_scope,
            "kind": args.kind,
            "oversized": args.oversized or None,
        })
        if len(args.files) > MAX_CONTRACT_FILES and not args.oversized:
            print(f"  warning: step {args.id} lists {len(args.files)} files (> {MAX_CONTRACT_FILES}) "
                  f"and is not marked oversized — it will refuse to lock. Split it.", file=sys.stderr)
        print(f"step {args.id} added")
        return 0

    if args.cmd == "plan-show":
        print(render_plan(root))
        return 0

    if args.cmd == "plan-next":
        step = next_todo_step(root)
        print(step["id"] if step else "")
        return 0

    if args.cmd == "plan-step":
        step = get_step(root, args.id)
        if not step:
            print(f"step {args.id} not in plan", file=sys.stderr)
            return 1
        print(json.dumps(step, indent=2))
        return 0

    if args.cmd == "step-status":
        found = set_step_status(root, args.id, args.status)
        print(f"step {args.id} -> {args.status}" if found else f"step {args.id} not in plan",
              file=sys.stdout if found else sys.stderr)
        return 0 if found else 1

    if args.cmd == "lock":
        files = _abspaths(root, args.files)
        plan = load_plan(root)
        plan_step = get_step(root, args.id)
        if plan and plan_step is None:
            print(f"step {args.id} is not in the plan — plan it first or use a real step id",
                  file=sys.stderr)
            return 1
        kind = (plan_step or {}).get("kind") or args.kind
        if kind == "refactor" and args.acceptance:
            print("a refactor step must carry NO acceptance criteria (it asserts no new behaviour) — "
                  "drop --acceptance, or lock it --kind story", file=sys.stderr)
            return 1
        oversized = bool((plan_step or {}).get("oversized"))
        if len(files) > MAX_CONTRACT_FILES and not oversized:
            print(f"contract has {len(files)} files (> {MAX_CONTRACT_FILES}) — a step this big isn't "
                  f"small/controllable. Split it, or mark the plan step oversized.", file=sys.stderr)
            return 1
        save_current_story(root, {
            "id": args.id,
            "title": args.title,
            "points": args.points,
            "files": files,
            "acceptance": args.acceptance,
            "out_of_scope": args.out_of_scope,
            "kind": kind,
            "red_criteria": [],
            "status": "in-progress",
        })
        set_step_status(root, args.id, "current")
        print(current_story_path(root))
        return 0

    if args.cmd == "add-file":
        story = load_current_story(root) or {"files": []}
        story.setdefault("files", [])
        story["files"] = sorted(set(story["files"]) | set(_abspaths(root, args.files)))
        save_current_story(root, story)
        print(current_story_path(root))
        return 0

    if args.cmd == "mark-red":
        story = load_current_story(root)
        if not story:
            print("no active step", file=sys.stderr)
            return 1
        acceptance = story.get("acceptance") or []
        crit = (args.criterion or "").strip()
        reds = set(story.get("red_criteria") or [])
        if acceptance:
            match = next((a for a in acceptance if _norm(a) == _norm(crit)), None) if crit else None
            if not match:
                print("name the failing criterion with --criterion; it must match one of:\n  "
                      + "\n  ".join(acceptance), file=sys.stderr)
                return 1
            reds.add(match)
            covered = sum(1 for a in acceptance if a in reds)
            story["red_criteria"] = sorted(reds)
            save_current_story(root, story)
            print(f"red observed ({covered}/{len(acceptance)} criteria)")
        else:
            reds.add(crit or "red")
            story["red_criteria"] = sorted(reds)
            save_current_story(root, story)
            print("red observed")
        return 0

    if args.cmd == "check-tdd":
        story = load_current_story(root)
        if not story:
            print("no active step", file=sys.stderr)
            return 1
        if story.get("kind") == "refactor":
            print("refactor: no new red test required (existing tests are the gate)")
            return 0
        if not (story.get("acceptance") or []):
            print("this non-refactor step declares no acceptance criteria — nothing was test-driven. "
                  "Add criteria, or lock it --kind refactor if it changes no behaviour.", file=sys.stderr)
            return 1
        ok, missing = criteria_covered(story)
        if ok:
            print("TDD: every acceptance criterion has a matching red test")
            return 0
        print(f"TDD: {missing} acceptance criterion(criteria) without a recorded red test — "
              f"write the failing test and run mark-red --criterion before closing", file=sys.stderr)
        return 1

    if args.cmd == "lean-debt":
        files = _abspaths(root, args.files) if args.files else None
        ledger = scan_lean_debt(root, files)
        if not ledger:
            print("No lean: debt. Clean ledger.")
            return 0
        for row in ledger:
            upgrade = f" — upgrade: {row['upgrade']}" if row["upgrade"] else ""
            rot = "  [no-trigger]" if row["no_trigger"] else ""
            print(f"  {row['file']}:{row['line']} — {row['ceiling']}{upgrade}{rot}")
        no_trig = sum(1 for r in ledger if r["no_trigger"])
        print(f"{len(ledger)} marker(s), {no_trig} with no trigger.")
        return 0

    if args.cmd == "close":
        story = load_current_story(root)
        if story and story.get("id") is not None:
            set_step_status(root, story["id"], "done")
        clear_current_story(root)
        print("step closed" + (f" (step {story['id']} marked done)" if story else ""))
        return 0

    if args.cmd == "status":
        print(render_plan(root))
        story = load_current_story(root)
        if story:
            ok, missing = criteria_covered(story)
            tdd = "all criteria red" if ok else f"{missing} criterion(criteria) still need a red test"
            print(f"\nActive lock: step {story.get('id')} — {story.get('title', '')}")
            print(f"  files: {', '.join(os.path.relpath(f, root) for f in story.get('files', []))}")
            print(f"  tdd: {tdd}")
        elif has_unfinished_plan(root):
            print("\nNo active lock. Run /up:run to lock the next step.")
        else:
            blocked = blocked_steps(root)
            if blocked:
                print(f"\nNo active lock. {len(blocked)} step(s) blocked "
                      f"({', '.join(str(s['id']) for s in blocked)}) — re-drive with /up:run <id> "
                      f"or accept the gap.")
            else:
                print("\nNo active lock.")
        return 0

    if args.cmd == "abort":
        story = load_current_story(root)
        if story:
            set_step_status(root, story.get("id"), "blocked")
        clear_current_story(root)
        print("active step aborted (lock released, step marked blocked; plan intact)")
        return 0

    if args.cmd == "show":
        if os.path.isfile(config_path(root)):
            print(json.dumps(load_config(root), indent=2))
        else:
            print("no .scrum/config.json (run /up:init)")
        return 0

    if args.cmd == "doctor":
        report = check_dependencies(root)
        mcp_guidance = dict(_MCP_DEPS)
        for rec in report:
            print(f"  [{'OK' if rec['present'] else 'MISSING'}] {rec['name']} ({rec['kind']})")
        missing_mcp = [r for r in report if r["kind"] == "mcp" and not r["present"]]
        if missing_mcp:
            print("\nTo install missing MCP deps, run manually:")
            for rec in missing_mcp:
                print(f"  {mcp_guidance[rec['name']]}")
        return 1 if missing_mcp else 0

    if args.cmd == "bootstrap":
        results = bootstrap_tools(root)
        for rec in results:
            print(f"  {rec['name']:12} {'ok' if rec['ok'] else 'FAIL'}")
            if not rec["ok"] and rec["output"]:
                print(f"    {rec['output'][:200]}")
        if all(r["ok"] for r in results):
            print("  repo-local .codegraph/ present")
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(_cli())
