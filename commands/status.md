---
description: Show the plan and active lock; or recover — abort | split | add-file | red | done. The inspect-and-escape surface.
argument-hint: "[abort | split | add-file <path> | red <criterion> | done <id>]"
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, Agent
---

Inspect where the plan is, and recover when something wedges. Sub-command from `$ARGUMENTS`
(default: show). These fold every escape hatch into one discoverable place — no hand-editing of
`.scrum/`.

## (default) show

Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" status`. It prints the plan
(done/current/remaining), the active lock (files, and which acceptance criteria still need a red
test), and points the user at the next action. Read-only.

## abort

Release a wedged step: `scrum_state.py abort`. It clears the active lock and marks the step
`blocked` in the plan (the rest of the plan stays intact). Use when a step can't be finished now —
`/up:run` will skip past `blocked`/`done` steps; re-open one later by re-running `/up:plan` or
`/up:run <id>`.

## split

Re-decompose the current or an oversized step that turned out too big. Invoke the `step-planner`
agent on that step's intent, present the smaller steps, and on approval rewrite them into the plan
(`plan-add` the replacements with fresh ids; mark the original `aborted`). Then `/up:run` continues
on the smaller steps. Note: `plan-add` appends, so replacement steps land at the end of the plan —
if later steps depend on them, tell the user to re-order (or split before starting those steps).

## add-file <path> [<path> …]

Widen the locked contract mid-step for a legitimately-needed file (e.g. a caller the brief missed,
or a hotfix that must touch one more file): `scrum_state.py add-file --file <path> [--file …]`.
State why before adding. Scope-guard then allows edits to it.

## red <criterion>

Manually record a failing test for a criterion: `scrum_state.py mark-red --criterion '<criterion>'`.
The implementer normally does this; use it when driving a step by hand.

## done <id>

Force-close a step past a blocking gate or review — the explicit, deliberate override. Ask the user
for a one-line reason, then run `step-status --id <id> --status done` and `close`. Report the
override and its reason prominently (which checks were red / which blocker was accepted) so the
decision stays visible. Use sparingly; the gates exist for a reason.
