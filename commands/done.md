---
description: Finish the active story — navigator review, then the done-gate (verify set). Closes only when both pass.
argument-hint: ""
allowed-tools: Bash, Read, Glob, Grep, Edit, Agent
---

Close the active story in `.scrum/current-story.json`. If there is none, tell the user to
`/up:story start` first and stop.

1. **Navigator review.** Invoke the `navigator` agent with the story's brief and contract. It
   returns a verdict and severity-tagged findings.

2. **Block on blockers.** If any `blocker` findings are open, show them and STOP — do not close.
   Hand them to the implementer to fix test-first, then re-run `/up:done`. Repeat until the verdict
   is `pass`. This is the review gate: a story cannot close with open blockers.

3. **Done-gate (verify set).** Run:
   `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/done-gate.py"`
   It runs the configured `test`, `lint`, `typecheck`, and `smoke` commands. If it exits non-zero,
   show the failing output and STOP — the story cannot close on a red gate.

4. **Close** (only after both pass):
   - mark the story `done` in `.scrum/sprint.md` (this tags the increment);
   - run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" close` to release the lock.
   Then report what shipped and suggest the next `/up:story start`, or `/up:sprint close` if the
   sprint is complete.
