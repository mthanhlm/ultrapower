#!/usr/bin/env python3
"""Shared state helpers for the ultrapower plugin's per-project `.scrum/` directory.

Layout under `<project>/.scrum/`:
  config.json         machine-read: verify commands, Definition of Done
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
import re
import shutil
import subprocess
import sys

SCRUM_DIRNAME = ".scrum"

DEFAULT_CONFIG = {
    "scrum_visibility": "local",
    "lean_mode": "full",
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
    "tutored.md": "# Tutored\n\n_What `/up:tutor` has taught you, tagged by source (a story id or `project`). Deduped._\n",
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


LEAN_MODES = ("off", "lite", "full", "ultra")
DEFAULT_LEAN_MODE = "full"
_LADDER_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lean", "ladder.md")


def _normalize_lean_mode(value):
    if isinstance(value, str) and value.strip().lower() in LEAN_MODES:
        return value.strip().lower()
    return None


def resolve_lean_mode(root):
    """Active lean intensity: UP_LEAN_MODE env > config `lean_mode` > `full`. Invalid values ignored."""
    return (_normalize_lean_mode(os.environ.get("UP_LEAN_MODE"))
            or _normalize_lean_mode(load_config(root).get("lean_mode"))
            or DEFAULT_LEAN_MODE)


def _filter_ladder_for_mode(body, mode):
    # lean: keyed off **mode** tokens in the one Intensity table; a second mode-named table would need anchoring
    others = tuple(f"**{m}**" for m in LEAN_MODES if m != mode)
    return "\n".join(
        line for line in body.splitlines()
        if not (line.lstrip().startswith("|") and any(tok in line for tok in others))
    )


def ladder_text(mode=DEFAULT_LEAN_MODE, path=_LADDER_PATH):
    """The lean ladder filtered to `mode`. Empty when mode is `off` or the file is unreadable."""
    mode = _normalize_lean_mode(mode) or DEFAULT_LEAN_MODE
    if mode == "off":
        return ""
    try:
        with open(path) as f:
            body = f.read()
    except (OSError, ValueError):
        return ""
    return _filter_ladder_for_mode(body, mode)


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


def _read_text(path, default=""):
    try:
        with open(path) as f:
            return f.read()
    except OSError:
        return default


def _set_table_status(text, story_id, status):
    out = []
    found = False
    for line in text.splitlines(keepends=True):
        body = line.rstrip("\n")
        cells = body.split("|")
        if body.startswith("|") and len(cells) >= 4 and cells[1].strip() == story_id:
            cells[-2] = f" {status} "
            out.append("|".join(cells) + ("\n" if line.endswith("\n") else ""))
            found = True
        else:
            out.append(line)
    return "".join(out), found


def mark_story_done(root, story_id):
    """Flip a story's sprint.md row to `done` by id. Idempotent; False if the id is absent."""
    path = os.path.join(scrum_dir(root), "sprint.md")
    new_text, found = _set_table_status(_read_text(path), story_id, "done")
    if found:
        with open(path, "w") as f:
            f.write(new_text)
    return found


def record_velocity(root, sprint, goal, committed, completed):
    """Upsert a velocity row keyed by sprint. True if appended, False if a row was updated in place."""
    path = os.path.join(scrum_dir(root), "velocity.md")
    row = f"| {sprint} | {goal} | {committed} | {completed} |"
    out, replaced = [], False
    for line in _read_text(path, SCAFFOLD["velocity.md"]).splitlines():
        cells = line.split("|")
        if line.startswith("|") and len(cells) >= 5 and cells[1].strip() == str(sprint):
            out.append(row)
            replaced = True
        else:
            out.append(line)
    if not replaced:
        out.append(row)
    with open(path, "w") as f:
        f.write("\n".join(out) + "\n")
    return not replaced


def draft_retro(root, sprint, goal, committed, completed):
    """Append a dated DRAFT retro section to retro.md, newest-first. Skips when a draft for this
    sprint already exists, so it never clobbers manual edits. True if a draft was added."""
    path = os.path.join(scrum_dir(root), "retro.md")
    text = _read_text(path, SCAFFOLD["retro.md"])
    if f"## Sprint {sprint} —" in text:
        return False
    draft = (
        f"## Sprint {sprint} — DRAFT <!-- edit me, then delete this DRAFT marker -->\n\n"
        f"_Goal: {goal} · {completed}/{committed} pts completed._\n\n"
        f"**Went well** — \n\n**Hurt** — \n\n**One change to try** — \n\n"
        f"**Learned** (seed for `/up:tutor`) — \n\n"
    )
    cut = text.find("\n## ")
    if cut != -1:
        new = text[:cut + 1] + draft + text[cut + 1:]
    else:
        new = text.rstrip("\n") + "\n\n" + draft
    with open(path, "w") as f:
        f.write(new)
    return True


def _normalize_topic(topic):
    return " ".join(topic.lower().split())


def _learning_topics(text, source):
    topics = set()
    in_section = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_section = line[3:].strip() == source
        elif in_section and line.startswith("- "):
            topics.add(_normalize_topic(line[2:].split(" — ", 1)[0]))
    return topics


def record_learning(root, source, topic, note=""):
    """Append a learning under its `## <source>` section in tutored.md, deduped by
    (source, normalized topic). Returns False when an equivalent entry already exists."""
    path = os.path.join(scrum_dir(root), "tutored.md")
    text = _read_text(path, SCAFFOLD["tutored.md"])
    if _normalize_topic(topic) in _learning_topics(text, source):
        return False
    entry = "- " + topic + (f" — {note}" if note else "")
    lines = text.splitlines()
    header = f"## {source}"
    if header in lines:
        insert_at = lines.index(header) + 1
        start = insert_at
        while insert_at < len(lines) and not lines[insert_at].startswith("## "):
            insert_at += 1
        while insert_at > start and lines[insert_at - 1].strip() == "":
            insert_at -= 1
        lines.insert(insert_at, entry)
    else:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines += [header, entry]
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return True


def _pending_ids(text):
    ids, in_pending = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            in_pending = line[3:].strip() == "Pending"
        elif in_pending and line.startswith("- "):
            ids.append(line[2:].split(" — ", 1)[0].strip())
    return ids


def list_pending(root):
    return _pending_ids(_read_text(os.path.join(scrum_dir(root), "tutored.md"), SCAFFOLD["tutored.md"]))


def queue_tutor(root, story_id, title=""):
    """Add a story to the '## Pending' tutoring queue in tutored.md, deduped by id.
    Returns False if it is already queued."""
    path = os.path.join(scrum_dir(root), "tutored.md")
    text = _read_text(path, SCAFFOLD["tutored.md"])
    if story_id in _pending_ids(text):
        return False
    entry = f"- {story_id}" + (f" — {title}" if title else "")
    lines = text.splitlines()
    if "## Pending" in lines:
        i = lines.index("## Pending") + 1
        while i < len(lines) and not lines[i].startswith("## "):
            i += 1
        while i > 0 and lines[i - 1].strip() == "":
            i -= 1
        lines.insert(i, entry)
    else:
        cut = next((k for k, ln in enumerate(lines) if ln.startswith("## ")), len(lines))
        section = ["## Pending", "", entry, ""]
        if cut > 0 and lines[cut - 1].strip() != "":
            section = [""] + section
        lines[cut:cut] = section
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return True


def unqueue_tutor(root, story_id):
    """Remove a story from the '## Pending' queue. Returns True if it was present."""
    path = os.path.join(scrum_dir(root), "tutored.md")
    out, in_pending, removed = [], False, False
    for line in _read_text(path, SCAFFOLD["tutored.md"]).splitlines():
        if line.startswith("## "):
            in_pending = line[3:].strip() == "Pending"
        elif in_pending and line.startswith("- ") and line[2:].split(" — ", 1)[0].strip() == story_id:
            removed = True
            continue
        out.append(line)
    if removed:
        with open(path, "w") as f:
            f.write("\n".join(out) + "\n")
    return removed


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
    p_markdone = sub.add_parser("mark-done")
    p_markdone.add_argument("--id", required=True)
    p_vel = sub.add_parser("record-velocity")
    p_vel.add_argument("--sprint", required=True)
    p_vel.add_argument("--goal", default="")
    p_vel.add_argument("--committed", type=int, default=0)
    p_vel.add_argument("--completed", type=int, default=0)
    p_retro = sub.add_parser("draft-retro")
    p_retro.add_argument("--sprint", required=True)
    p_retro.add_argument("--goal", default="")
    p_retro.add_argument("--committed", type=int, default=0)
    p_retro.add_argument("--completed", type=int, default=0)
    p_learn = sub.add_parser("record-learning")
    p_learn.add_argument("--source", required=True)
    p_learn.add_argument("--topic", required=True)
    p_learn.add_argument("--note", default="")
    p_pend = sub.add_parser("tutor-pending")
    p_pend.add_argument("--add")
    p_pend.add_argument("--title", default="")
    p_pend.add_argument("--remove")
    p_pend.add_argument("--list", action="store_true")
    p_debt = sub.add_parser("lean-debt")
    p_debt.add_argument("--file", action="append", default=None, dest="files")
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
    if args.cmd == "mark-done":
        found = mark_story_done(root, args.id)
        print(f"marked {args.id} done" if found else f"{args.id} not in sprint.md",
              file=sys.stdout if found else sys.stderr)
        return 0 if found else 1
    if args.cmd == "record-velocity":
        appended = record_velocity(root, args.sprint, args.goal, args.committed, args.completed)
        print("velocity recorded" if appended else "velocity updated")
        return 0
    if args.cmd == "draft-retro":
        added = draft_retro(root, args.sprint, args.goal, args.committed, args.completed)
        print("retro draft added" if added else "retro draft already exists — left untouched")
        return 0
    if args.cmd == "record-learning":
        added = record_learning(root, args.source, args.topic, args.note)
        print("learning recorded" if added else "already recorded — skipped (deduped)")
        return 0
    if args.cmd == "tutor-pending":
        if args.add:
            print("queued for tutoring" if queue_tutor(root, args.add, args.title) else "already queued")
        elif args.remove:
            print("removed from queue" if unqueue_tutor(root, args.remove) else "not in queue")
        else:
            ids = list_pending(root)
            print("\n".join(ids) if ids else "(none pending)")
        return 0
    if args.cmd == "lean-debt":
        files = None
        if args.files:
            files = [os.path.realpath(f if os.path.isabs(f) else os.path.join(root, f)) for f in args.files]
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
    cfg["scrum_visibility"] = args.scrum_mode
    cfg["verify"] = {"test": args.test, "lint": args.lint, "typecheck": args.typecheck, "smoke": args.smoke}
    save_config(root, cfg)
    scaffold(root)
    sync_gitignore(root)
    print(config_path(root))
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
