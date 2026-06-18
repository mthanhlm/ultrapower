---
description: Drive the plan's steps test-first — lock, implement, review, gate, close, advance. `all` runs autonomously and pauses only at boundaries.
argument-hint: "[all | <step-id>]"
allowed-tools: Bash, Read, Glob, Grep, Edit, Agent
---

Execute the plan written by `/up:plan`. Requires `.scrum/plan.json`; if there is none, tell the user
to `/up:plan <task>` first and stop. From `$ARGUMENTS`: `all` (default — drive the whole plan) or a
specific `<step-id>` (drive exactly one step, then stop — the tight-control lane).

## Per-step cycle

For the target step (for `all`, repeatedly take `scrum_state.py plan-next`):

1. **Boundary — too big.** Read the step with `scrum_state.py plan-step --id <id>`. If it carries an
   `oversized` flag OR its `points` are `> 3`, STOP and report it — the user splits it
   (`/up:status split`) or accepts and re-runs `/up:run <id>` to force it. Do not auto-drive a step
   that isn't small. (`lock` also hard-refuses a contract larger than 6 files unless marked oversized.)

2. **Lock the contract** read verbatim from `plan-step` — never fabricate or trim the file list:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" lock --id <id> --title '<t>' \
     --points <n> --file <path> [--file …] --acceptance '<c>' [--acceptance …] --out '<out>'
   ```
   Pass the step's `files`, `acceptance`, and `out_of_scope` exactly as `plan-step` reported them.
   The step's `kind` (story vs refactor) is set by the planner and carried automatically — do not
   invent `--kind refactor` at run time. Locking arms scope-guard + tdd-guard and clears plan-guard.

3. **Implement.** Invoke the `implementer` agent (opus, deep reasoning) with the locked contract. It
   does red → green → refactor, marking each acceptance criterion red as it goes (`mark-red
   --criterion '<exact acceptance text>'` — the criterion must match a locked acceptance string or it
   is rejected). **Source is written only via the Edit/Write/serena tools, never shell redirection**
   (`echo >`, `sed -i`, `tee`, heredocs) — the bash-guard blocks shell source-writes, and only the
   edit tools route through scope + TDD. It stays inside the contract; if it reports an off-contract
   need, extend scope with `/up:status add-file` and continue — do not edit code yourself here.

4. **Review (the single gate).** Invoke the `navigator` agent on the diff. It runs Logical+Flow
   always and the polish lenses for >2pt steps. **For a risky step** (touches code with many callers,
   a security/money/data path, or the planner flagged it), run the review as a small panel: 3
   independent `navigator` invocations, and treat a finding as a real blocker when ≥2 agree.
   **Boundary — blockers:** if any blocker is open, STOP and report it; hand it back to the
   implementer to fix test-first, then re-review. Do not close with open blockers.

5. **TDD gate.** Run `scrum_state.py check-tdd` (skip for `--kind refactor`). It fails if any
   acceptance criterion lacks a recorded red test — every criterion must have been driven test-first.
   If it fails, send it back to the implementer.

6. **Done-gate.** Run `python3 "${CLAUDE_PLUGIN_ROOT}/hooks/done-gate.py"`. It runs the configured
   verify set in parallel (120s/check). **Boundary — red gate:** if it exits non-zero, STOP, show the
   failing output, and do not close.

7. **Close + advance.** Only after review passes, `check-tdd` passes, and the gate is green:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" close
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" lean-debt --file <each step file>
   ```
   `close` atomically marks the step `done` and releases the lock (so a dropped status update can't
   strand the step). Surface any `lean:` debt (especially `[no-trigger]`) in your report —
   informational, never blocks. For `all`, advance to the next step; for a single `<step-id>`, stop.

## Boundaries (where `all` pauses and hands back to you)

An oversized/split-refused step, an open review blocker, a red done-gate, or the plan completing.
That is the only time `/up:run all` stops — otherwise it drives top-to-bottom unattended.
**Never commit:** leave all changes in the working tree for one human review at plan end. `all`
skips `blocked` steps (aborted earlier) rather than retrying them — re-drive one explicitly with
`/up:run <id>`. When the plan completes, report what shipped, any skipped/blocked steps, and the
accumulated `lean:` debt.
