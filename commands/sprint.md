---
description: Plan or close a sprint. `plan` runs a guided question-bundle to set a crisp sprint goal + clear backlog; `close` records velocity.
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
   - constraints (deadline, must-not-break, dependencies);
   - how big the sprint should be — anchor on recent velocity from `velocity.md`.
   Always offer a "you pick" default and recommend one. On a **brand-new project** (empty
   backlog) widen the first batch to capture the product vision before narrowing to the goal.

3. **Draft via the scrum-master.** Invoke the `scrum-master` agent with the intake answers plus
   the current backlog and velocity. It returns a draft: a one-line **sprint goal**, a set of
   **stories** (each with acceptance criteria and a *proposed* point estimate + rationale), and
   a capacity note vs. velocity.

4. **Confirm with the user.** Present the draft. The user edits goal, stories, and scope and —
   per the estimation rule — confirms or overrides each point estimate. Iterate until approved.

5. **Write state** with the approved result:
   - `.scrum/sprint.md` — goal, length (`sprint_length_days` from config), start date
     (`date +%Y-%m-%d`), committed points, and the story table with status `todo`.
   - `.scrum/backlog.md` — remove the pulled-in stories; keep the rest.
   Then point the user to `/up:story start <id>` to begin the first story.

## close

1. Read `.scrum/sprint.md`. If any story is not `done`, list them and ask whether to close
   anyway (carry them back to the backlog) or stop.
2. Compute committed vs. completed points. Append a row to `.scrum/velocity.md`
   (`| goal | committed | completed |`).
3. Reset `.scrum/sprint.md` to the no-active-sprint scaffold, moving unfinished stories back
   into `.scrum/backlog.md`.
4. Summarise the outcome and suggest `/up:retro` to capture lessons before the next `plan`.
