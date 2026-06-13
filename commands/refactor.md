---
description: Refactor safely — codegraph impact first, lock scope, restructure with tests green throughout. No behavior change.
argument-hint: "<symbol or area to refactor>"
allowed-tools: Bash, Read, Glob, Grep, Edit, Write, AskUserQuestion, Agent
---

Restructure code without changing behavior. The safety net is the existing test suite — green
before and after. Requires `/up:init`.

1. **Impact first.** Use codegraph (`codegraph_impact` / callers) on the target `$ARGUMENTS` to
   list every affected site. Refactoring without this is the top way to break callers silently.
   For anything non-trivial, delegate to the `story-planner` agent (read-only) for the brief.

2. **Green baseline.** Run the `test` command from `.scrum/config.json`. If it is not green, STOP
   — fix or commit first; never refactor on red.

3. **Lock scope.** Lock the files to touch (sources + their tests):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" lock \
     --id refactor --title '<target>' --file <path> [--file <path> ...]
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" mark-red
   ```
   The existing green tests are the gate, so source edits unlock without a new failing test —
   a refactor adds no behavior, so it needs no new test.

4. **Refactor.** Make the structural change — prefer serena symbol edits. Update every affected
   site from step 1. No new behavior, no features, no drive-by edits.

5. **Stay green.** Re-run the `test` command; it must still pass with the tests unchanged (changed
   assertions would mean changed behavior). Then `/up:done` to review, gate, and close.
