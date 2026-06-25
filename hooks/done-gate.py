#!/usr/bin/env python3
"""Step done-gate: run the project's verify set and report pass/fail.

Invoked by `/up:run` before a step closes. Reads `.scrum/config.json` verify commands and runs
each non-empty one in the project root, IN PARALLEL with a per-check timeout, so a slow check
never serializes behind the others and a hung/watch-mode command can't freeze the close for tens
of minutes. Exits 0 only if all configured checks pass; exits 1 with the failing output otherwise.
A step must not close on a red gate. Optional positional argv overrides the cwd.

`--checks a,b` runs only the named subset (e.g. the fast checks at every step close), so
`/up:run all` can defer the full `test` suite to one run at plan-end instead of re-running it on
every close. No `--checks` ⇒ the full configured set, as before.
"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

_PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_PLUGIN_ROOT, "scripts"))
import scrum_state  # noqa: E402

ORDER = ("test", "lint", "typecheck", "smoke")
# lean: 120s/check, ample for unit suites + a boot smoke; raise per-project in config if a real suite needs it
TIMEOUT = 120


def _run_one(root, name, cmd):
    try:
        proc = subprocess.run(cmd, cwd=root, shell=True, capture_output=True,
                              text=True, timeout=TIMEOUT)
        return name, proc.returncode == 0, (proc.stdout + proc.stderr)[-2000:]
    except subprocess.TimeoutExpired:
        return name, False, f"timed out after {TIMEOUT}s (a watch/serve command can't be a verify check)"
    except OSError as exc:
        return name, False, str(exc)


def run_gate(root, only=None):
    verify = scrum_state.load_config(root).get("verify", {})
    names = [n for n in ORDER if only is None or n in only]
    active = {name: (verify.get(name) or "").strip() for name in names}
    active = {name: cmd for name, cmd in active.items() if cmd}
    outcomes = {}
    if active:
        with ThreadPoolExecutor(max_workers=len(active)) as pool:
            for name, ok, out in pool.map(lambda kv: _run_one(root, *kv), active.items()):
                outcomes[name] = (ok, out)
    return [(name, *outcomes.get(name, (None, ""))) for name in names]


def main(argv=None):
    argv = list(argv or [])
    only = None
    if "--checks" in argv:
        i = argv.index("--checks")
        if i + 1 < len(argv):
            only = {c.strip() for c in argv[i + 1].split(",") if c.strip()}
        del argv[i:i + 2]
    cwd = (argv or [None])[0] or os.getcwd()
    root = scrum_state.find_project_root(cwd)
    if not scrum_state.load_current_story(root):
        print("no active step (nothing to gate)", file=sys.stderr)
        return 1
    results = run_gate(root, only)
    for name, ok, _ in results:
        mark = "skip" if ok is None else ("pass" if ok else "FAIL")
        print(f"  {name:9} {mark}")
    failed = [(name, output) for name, ok, output in results if ok is False]
    if failed:
        print("\nDone-gate: FAILED — fix before closing the step:", file=sys.stderr)
        for name, output in failed:
            print(f"\n[{name}]\n{output}", file=sys.stderr)
        return 1
    print("Done-gate: all configured checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
