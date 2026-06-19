#!/usr/bin/env python3
"""PostToolUse hook: keep codegraph fresh and pull an edit's ripples into scope.

After an in-contract edit in a codegraph project, reindex incrementally, then -- when a
step is locked -- check whether the edit's dependents (codegraph `affected` tests and
`callers` of its symbols) fall outside the step contract. If they do, block (exit 2) so the
agent must bring the ripples into scope. No locked step, no `.codegraph`, or any error ->
do nothing (fail-open).
"""
import json
import os
import re
import subprocess
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

PATH_KEYS = ("file_path", "notebook_path", "relative_path")
TEXT_KEYS = ("new_string", "old_string", "content", "body")

# Definition kinds a `codegraph query` node must carry to count toward name-collision detection.
_DEF_KINDS = {"function", "class", "method", "interface", "struct", "enum"}

# lean: regex symbol-extraction for common langs; swap in a per-language parser if it misbehaves.
_SYMBOL = re.compile(
    r"^\s*(?:def|class|func)\s+(\w+)|"
    r"\bfunction\s+(\w+)|"
    r"\b(?:const|let|var)\s+(\w+)\s*=",
    re.M,
)


def _symbols(text):
    return {name for m in _SYMBOL.finditer(text) for name in m.groups() if name}


def _payload_symbols(tool_input):
    # lean: extract from the edit payload (not the whole file) so we only weigh symbols we
    # actually changed -- including old_string to catch renames/deletions. Body-only edits that
    # omit the def line are a deliberate false-negative ceiling (safer than false-positives).
    texts = [tool_input[k] for k in TEXT_KEYS if isinstance(tool_input.get(k), str)]
    texts += [e[k] for e in (tool_input.get("edits") or []) if isinstance(e, dict)
              for k in ("new_string", "old_string") if isinstance(e.get(k), str)]
    return _symbols("\n".join(texts))


def _cg_json(args, root, timeout=5):
    try:
        out = subprocess.run(["codegraph", *args], cwd=root,
                             capture_output=True, text=True, timeout=timeout)
        return json.loads(out.stdout)
    except Exception:
        return None


def _defined_in_one_file(name, root):
    # Collision guard: callers can only be attributed to a symbol defined in exactly one file.
    nodes = _cg_json(["query", name, "-j", "-l", "50"], root)
    if not isinstance(nodes, list):
        return False
    files = set()
    for entry in nodes:
        node = (entry or {}).get("node") if isinstance(entry, dict) else None
        if isinstance(node, dict) and node.get("name") == name and node.get("kind") in _DEF_KINDS:
            files.add(node.get("filePath"))
    return len(files) == 1


def _dependent_relpaths(edited_abs, tool_input, root):
    rels = set()
    affected = _cg_json(["affected", edited_abs, "-j"], root)
    if affected:
        rels.update(t.get("filePath") for t in (affected.get("affectedTests") or []))
    for name in _payload_symbols(tool_input):
        if not _defined_in_one_file(name, root):
            continue
        callers = _cg_json(["callers", name, "-j"], root)
        if callers:
            rels.update(c.get("filePath") for c in (callers.get("callers") or []))
    return {r for r in rels if r}


def main():
    data = json.load(sys.stdin)
    cwd = data.get("cwd") or os.getcwd()
    tool_input = data.get("tool_input") or {}
    raw = next((tool_input[k] for k in PATH_KEYS if tool_input.get(k)), None)
    if not raw:
        return 0
    root = scrum_state.find_project_root(cwd)
    # lean: only act inside a codegraph-indexed project, else every edit anywhere would
    # spawn codegraph. Drop this fast-path if impact-guard ever ships its own indexer.
    if not os.path.isdir(os.path.join(root, ".codegraph")):
        return 0
    try:
        subprocess.run(["codegraph", "sync", "-q"], cwd=root,
                       capture_output=True, text=True, timeout=10)
    except Exception:
        pass
    story = scrum_state.load_current_story(root)
    if not story:
        return 0
    contract = {os.path.realpath(f) for f in story.get("files", [])}
    edited_abs = os.path.realpath(raw if os.path.isabs(raw) else os.path.join(cwd, raw))
    dependents = {os.path.realpath(os.path.join(root, fp))
                  for fp in _dependent_relpaths(edited_abs, tool_input, root)}
    dependents -= {edited_abs}
    dependents -= contract
    if not dependents:
        return 0
    names = ", ".join(sorted(os.path.relpath(d, root) for d in dependents))
    print(
        f"Edit to {os.path.basename(edited_abs)} ripples to files outside the step contract: "
        f"{names}. A change that ripples must bring its ripples into scope -- add each "
        f"(python3 \"$CLAUDE_PLUGIN_ROOT\"/scripts/scrum_state.py add-file --file <path>) and "
        f"update it, or consciously justify skipping each.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
