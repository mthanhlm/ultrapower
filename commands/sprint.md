---
description: Plan or close a sprint. `plan` runs a guided question-bundle to set a crisp sprint goal + clear backlog; `close` records velocity and captures the retro.
argument-hint: "plan | close"
allowed-tools: Bash, Read, Glob, Write, AskUserQuestion, Agent
---

Manage the sprint for the current project. Requires `/up:init` first (needs `.scrum/config.json`);
if it is missing, tell the user to run `/up:init` and stop. Sub-command from `$ARGUMENTS`:
`plan` (default) or `close`.

## plan

Turn a rough intent into a crisp **sprint goal** and a **clear backlog** — by interviewing the
user the way a good planning session would, not by guessing.

1. **Load context**: read `.scrum/config.json`, `.scrum/backlog.md`, `.scrum/velocity.md`,
   `.scrum/sprint.md`. If a sprint is already active, ask whether to replace it; stop if not.

2. **Guided intake — the core of this command.** Ask the user a *bundle* of questions with
   AskUserQuestion to clear up the goal and scope before any work. Cover, in batches of up to 4:
   - the single outcome this sprint must deliver (the goal);
   - what is in scope and what is explicitly out;
   - constraints (must-not-break, dependencies);
   - how big the sprint should be — your call; points are a size signal, not a budget.
   Always offer a "you pick" default and recommend one. On a **brand-new project** (empty
   backlog) widen the first batch to capture the product vision before narrowing to the goal.

3. **Draft via the scrum-master.** Invoke the `scrum-master` agent with the intake answers plus
   the current backlog and velocity. It returns a draft: a one-line **sprint goal**, a set of
   **stories** (each with acceptance criteria and a *proposed* point estimate + rationale), and
   an informational point total (a size signal, not a budget — no scope-down verdict).

4. **Confirm with the user.** Present the draft. The user edits goal, stories, and scope and —
   per the estimation rule — confirms or overrides each point estimate. Iterate until approved.

5. **Write state** with the approved result:
   - **Renumber pulled-in backlog stories `B`→`S`** — each backlog item (`B<n>`) takes the next free
     sprint id (`S<n>`) on entering the sprint; the sprint table and `/up:story start` use the new `S` ids.
   - `.scrum/sprint.md` — goal, committed points (a size signal, not a budget), and the
     story table with status `todo`. No sprint length or start date — it is an open worklist
     closed on demand via `/up:sprint close`.
   - `.scrum/backlog.md` — remove the pulled-in stories; keep the rest.
   Then point the user to `/up:story start <id>` to begin the first story.

## close

1. Read `.scrum/sprint.md`. If any story is not `done`, list them and ask whether to close
   anyway (carry them back to the backlog) or stop.
2. Compute committed (sum of all story points) and completed (sum of `done` points), then record
   them automatically — no hand-editing:
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" record-velocity --sprint <n> --goal '<goal>' --committed <c> --completed <m>` upserts the `.scrum/velocity.md` row;
   - `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" draft-retro --sprint <n> --goal '<goal>' --committed <c> --completed <m>` seeds a dated **DRAFT** section in `.scrum/retro.md` (newest-first, never clobbering your edits).
3. **Capture the retro inline** — no separate command. Ask the user one small AskUserQuestion
   bundle: what went well, what slowed you down, and the single change to try next sprint. Offer
   "you pick" defaults drawn from the velocity numbers and the sprint outcome. The user may skip —
   then leave the seeded **DRAFT** as-is. Otherwise replace the draft's seed bullets with the
   answers and delete the `DRAFT` marker, keeping it to three: Went well / Hurt / One change to try.
4. Reset `.scrum/sprint.md` to the no-active-sprint scaffold, moving unfinished stories back
   into `.scrum/backlog.md` — **renumber carried-back stories `S`→`B`** (each takes the next free
   backlog id), the inverse of the `B`→`S` pull-in.
5. **Harvest the lean debt.** Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" lean-debt`
   (whole repo) and include the deferred-marker count, and any `[no-trigger]` rot, in the summary —
   so the shortcuts this sprint accumulated are visible before the next `plan`.
6. Summarise the outcome and suggest `/up:sprint plan` to start the next sprint with that change in mind.
