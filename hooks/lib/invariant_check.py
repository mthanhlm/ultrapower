#!/usr/bin/env python3
"""Architecture-invariant checks against .ultrapower/memory/codebase.toml.

Two modes:
  invariant_check.py <project_dir> <file_path>
      Content on stdin -> {"decision": "allow"|"ask"|"deny", "reason": "..."}.
      Used by PreToolUse (the live guard).

  invariant_check.py --disk <project_dir>
      Newline-separated file list on stdin -> human-readable violation lines for
      files as they now exist ON DISK. Used by the Stop edge-check (layer-2
      defense: catches a violation that landed via a path the live guard missed).

Read-only and fail-open: any problem -> allow / no findings.
"""
import sys, os, json, re, fnmatch

try:
    import tomllib
except Exception:
    print(json.dumps({"decision": "allow"}))
    sys.exit(0)


def load(path):
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception:
        return {}


def path_match(rel, pat):
    if fnmatch.fnmatch(rel, pat):
        return True
    if "**" in pat:
        if fnmatch.fnmatch(rel, pat.replace("/**", "/*")):
            return True
        prefix = pat.split("**", 1)[0].rstrip("/")
        if prefix and (rel == prefix or rel.startswith(prefix + "/")):
            return True
    return False


def import_match(content, pat):
    if "*" in pat:
        rx = re.escape(pat).replace(r"\*", ".*")
        return re.search(rx, content) is not None
    return pat in content


def load_invariants(proj):
    cb = load(os.path.join(proj, ".ultrapower", "memory", "codebase.toml"))
    return [i for i in cb.get("invariant", []) if isinstance(i, dict)]


def check(invs, proj, fp, content):
    try:
        rel = os.path.relpath(fp, proj)
    except Exception:
        rel = fp
    rel = rel.replace(os.sep, "/")
    worst, reason = None, ""
    for inv in invs:
        applies = inv.get("applies_to_paths") or ["**"]
        exempt = inv.get("exempt_paths") or []
        if not any(path_match(rel, p) for p in applies):
            continue
        if any(path_match(rel, p) for p in exempt):
            continue
        forb = inv.get("forbid_imports") or []
        hit = next((p for p in forb if import_match(content, p)), None)
        if not hit:
            continue
        sev = inv.get("severity", "warn")
        msg = f"{inv.get('id', 'invariant')}: {inv.get('rule', '')} (forbidden '{hit}' in {rel})."
        alt = inv.get("state_access")
        if alt:
            msg += f" Expected pattern: {alt}."
        if sev == "block":
            return "deny", msg
        if worst != "deny":
            worst, reason = "ask", msg
    return (worst or "allow"), reason


def main():
    args = sys.argv[1:]

    if args and args[0] == "--disk":
        proj = args[1] if len(args) > 1 else "."
        invs = load_invariants(proj)
        if not invs:
            return
        for line in sys.stdin:
            fp = line.strip()
            if not fp:
                continue
            path = fp if os.path.isabs(fp) else os.path.join(proj, fp)
            try:
                with open(path, "r", errors="ignore") as f:
                    content = f.read()
            except Exception:
                continue
            dec, reason = check(invs, proj, fp, content)
            if dec == "deny":
                print("VIOLATION: " + reason)
            elif dec == "ask":
                print("WARN: " + reason)
        return

    proj = args[0] if len(args) > 0 else "."
    fp = args[1] if len(args) > 1 else ""
    content = sys.stdin.read()
    invs = load_invariants(proj)
    if not invs:
        print(json.dumps({"decision": "allow"}))
        return
    dec, reason = check(invs, proj, fp, content)
    print(json.dumps({"decision": dec, "reason": reason}))


main()
