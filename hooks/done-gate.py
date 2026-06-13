#!/usr/bin/env python3
"""Story done-gate: run the project's verify set and report pass/fail.

Invoked by `/up:done`. Reads `.scrum/config.json` verify commands and runs each non-empty one
in the project root. Exits 0 only if all configured checks pass; exits 1 with the failing
output otherwise. A story must not close on a red gate. Optional argv[0] overrides the cwd.
"""
import os
import subprocess
import sys

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

ORDER = ("test", "lint", "typecheck", "smoke")
TIMEOUT = 600


def run_gate(root):
    verify = scrum_state.load_config(root).get("verify", {})
    results = []
    for name in ORDER:
        cmd = (verify.get(name) or "").strip()
        if not cmd:
            results.append((name, None, ""))
            continue
        try:
            proc = subprocess.run(cmd, cwd=root, shell=True, capture_output=True,
                                  text=True, timeout=TIMEOUT)
            results.append((name, proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]))
        except (subprocess.TimeoutExpired, OSError) as exc:
            results.append((name, False, str(exc)))
    return results


def main(argv=None):
    cwd = (argv or [None])[0] or os.getcwd()
    root = scrum_state.find_project_root(cwd)
    if not scrum_state.load_current_story(root):
        print("no active story (nothing to gate)", file=sys.stderr)
        return 1
    results = run_gate(root)
    for name, ok, _ in results:
        mark = "skip" if ok is None else ("pass" if ok else "FAIL")
        print(f"  {name:9} {mark}")
    failed = [(name, output) for name, ok, output in results if ok is False]
    if failed:
        print("\nDone-gate: FAILED — fix before closing the story:", file=sys.stderr)
        for name, output in failed:
            print(f"\n[{name}]\n{output}", file=sys.stderr)
        return 1
    print("Done-gate: all configured checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
