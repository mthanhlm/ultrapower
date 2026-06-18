---
description: Break a task into an ordered list of small (≤3pt) steps and write the plan. The forced-decomposition step.
argument-hint: "<task description>"
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, Agent
---

Turn one task into a plan of small, controllable steps. This is the plugin's core move: a task
worked as one bundle balloons in scope; the same task as a chain of small, separately-verified steps
stays lean. Requires `/up:init` (needs `.scrum/config.json`); if missing, say so and stop.

1. **Refuse to clobber an in-flight plan.** Run `scrum_state.py plan-next`. If it prints an id, a
   plan is still in progress — tell the user to finish it (`/up:run`) or clear it (`/up:status
   abort` for the active step; re-running `/up:plan` replaces the plan only after they confirm).

2. **Decompose — single pass by default.** Invoke the `step-planner` agent with the task
   (`$ARGUMENTS`). It grounds in codegraph and returns an ordered list of ≤3pt steps, each with a
   file contract, acceptance criteria, and an out-of-scope note. This is the right cost for the vast
   majority of tasks — do not escalate reflexively.

3. **Offer a deep pass only when the task is genuinely big or ambiguous.** If the step-planner
   returns multiple interpretations, flags any `oversized` step, or the decomposition runs long
   (roughly >5 steps), tell the user it looks large and **offer** (AskUserQuestion, recommend it) a
   deep pass — do not spend the tokens silently. On yes: spawn **2–3 independent `step-planner`
   agents** on the same task, then one judge pass (a final `step-planner` invocation given all
   drafts) to synthesise the most controllable decomposition, grafting the best splits. Bounded:
   2–3 planners + 1 judge, never more. Small/clear tasks skip this entirely.

4. **Confirm with the user.** Present the step list verbatim. The user edits scope, splits, files,
   and estimates. Do not edit any code. Iterate until approved. Every step must be ≤3pt or carry an
   explicit `oversized` reason the user has accepted.

5. **Write the plan** with the approved steps:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" plan-new --task '<task>'
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" plan-add --id 1 --title '<t>' \
     --points <n> --file <path> [--file …] --acceptance '<c>' [--acceptance …] \
     --out '<out>' [--kind refactor] [--oversized '<why it cannot split>']
   # …one plan-add per step, in order. Use --kind refactor (and NO --acceptance) for a
   # no-behaviour-change step; keep each step ≤3pt and ≤6 files or it will refuse to lock.
   ```
   The plan is stored as `.scrum/plan.json` (JSON, not a fragile markdown table). Show the written
   plan with `scrum_state.py plan-show`.

6. **Hand off.** Point the user to `/up:run all` to drive the whole plan autonomously (it pauses
   only at boundaries), or `/up:run <id>` to drive one step at a time.
