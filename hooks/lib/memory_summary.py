#!/usr/bin/env python3
"""Summarize .ultrapower TOML memory for context injection.

Usage:
  memory_summary.py summary    <project_dir>   -> full SessionStart summary
  memory_summary.py invariants <project_dir>   -> just the block-severity invariants

Read-only. Never raises to the caller; prints nothing on any problem.
"""
import sys, os

try:
    import tomllib
except Exception:
    sys.exit(0)


def load(path):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "summary"
    proj = sys.argv[2] if len(sys.argv) > 2 else "."
    mem = os.path.join(proj, ".ultrapower", "memory")

    cb = load(os.path.join(mem, "codebase.toml"))
    invs = [i for i in cb.get("invariant", []) if isinstance(i, dict)]
    block = [i for i in invs if i.get("severity") == "block"]

    if mode == "invariants":
        if not block:
            print("(none recorded yet — run /ultrapower:codegraph to capture architecture invariants)")
        else:
            for i in block:
                print(f"- {i.get('id', '?')}: {i.get('rule', '')}")
        return

    lines = []
    arch = cb.get("architecture", {})
    if isinstance(arch, dict) and arch.get("summary"):
        lines.append("Architecture: " + arch["summary"])
    if block:
        lines.append("Block invariants (the guard enforces these):")
        for i in block:
            lines.append(f"  - {i.get('id', '?')}: {i.get('rule', '')}")

    led = load(os.path.join(mem, "ledger.toml"))
    tasks = [t for t in led.get("task", []) if isinstance(t, dict)]
    doing = [t for t in tasks if t.get("status") == "doing"]
    nxt = [t for t in tasks if t.get("status") == "next"]
    if doing:
        lines.append("In progress:")
        for t in doing:
            lines.append(f"  - {t.get('id', '?')}: {t.get('summary', '')}")
    if nxt:
        lines.append("Next up:")
        for t in nxt[:5]:
            lines.append(f"  - {t.get('id', '?')}: {t.get('summary', '')}")

    dec = load(os.path.join(mem, "decisions.toml"))
    adrs = [a for a in dec.get("adr", []) if isinstance(a, dict)]
    rejected = [a for a in adrs if a.get("status") == "rejected-alternative" or a.get("rejected")]
    if rejected:
        lines.append("Previously rejected — do NOT rebuild:")
        for a in rejected[:5]:
            what = a.get("rejected") or a.get("title", "")
            why = a.get("why_rejected", "")
            lines.append(f"  - {what} — {why}")

    if lines:
        print("Project memory (.ultrapower):")
        print("\n".join(lines))


main()
