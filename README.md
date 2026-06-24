# ⚡ Ultrapower

A Claude Code plugin that forces a task into **small, controllable increments** and keeps each one
**lean and correct**. Plan a task into ≤3-point steps, drive them test-first with codegraph
grounding and a navigator review, and pass a verify-gate before any step closes — all under an
always-on **lean ladder** (YAGNI → stdlib → native → one line).

The mechanism is the point: a task taken as one bundle balloons in scope and slips control — for you
and for the agent. The same task as a chain of small, separately-verified steps stays lean. And the
decomposition is a **hook fact**, not a polite suggestion: while a plan has unfinished steps, you
cannot edit source — via the edit tools *or* shell redirection — outside a locked step.

What's hard-enforced vs. judged: *where* you edit (the locked contract) and *that* a plan is worked
step-by-step are enforced by hooks, and a step's size has a hard ceiling (a contract over 6 files
refuses to lock; a step over 3 points pauses the run). The ≤3-point *estimate* itself is the
planner's judgment plus your review of the plan — size is bounded by code and sharpened by you.

Commands are namespaced `/up:` (the plugin is named `up`).

## The loop

```
/up:init               once per project — check deps, detect verify commands, scaffold .scrum/
/up:plan <task>        break the task into an ordered list of small (≤3pt) steps → plan.json
/up:run all            drive every step autonomously, pausing only at boundaries:
  (per step)             lock contract → implementer (TDD red→green→refactor) →
                         navigator review → TDD gate → verify-gate → close → next step
/up:run <id>           drive exactly one step (tight-control lane)
/up:status             show the plan + active lock — or recover: abort | split | add-file | red | done
(always-on)            the lean ladder is injected every session — YAGNI → stdlib → native → one line
```

`/up:run all` walks the whole plan and only stops at a **boundary**: an oversized step, an open
review blocker, a red verify-gate, or the plan completing. It never commits — all changes stay in
the working tree for one human review at the end.

## How to use — a worked example

**"reject malformed emails on the signup form."**

**0. One-time setup** (per project): `/up:init` — checks codegraph is registered, detects
`test`/`lint`/`typecheck`/`smoke`, writes `.scrum/config.json`, gitignores `.scrum/`.

**1. Plan:** `/up:plan "reject malformed emails on signup"`. The **step-planner** grounds in the
codebase and returns a short ordered list of ≤3pt steps — e.g. *1. email-format validator (2pt); 2.
wire it into the signup handler (1pt)* — each with a file contract and acceptance criteria. Big or
ambiguous task? It offers a **deep pass** (a few independent planners + a judge) so the decomposition
is trustworthy. You approve; the plan is written to `plan.json`.

**2. Drive:** `/up:run all`. For each step it locks the file contract (now the scope and TDD guards
arm), hands the locked step to the **implementer** (which writes a failing test, marks it red, then
the minimal code to green, then refactors), runs the **navigator** review on the diff, checks every
acceptance criterion was driven test-first, then runs the verify-gate. Green + no blockers → the step
auto-closes and it advances. It pauses and reports only at a boundary.

**3. Recover when needed:** `/up:status` shows where you are. Hit a wall? `/up:status add-file` to
widen a contract, `/up:status split` to break up a step that turned out too big, `/up:status abort`
to release a wedged step, `/up:status done <id>` to consciously override a gate (with a recorded
reason).

## Commands

| Command | What it does |
|---|---|
| `/up:init` | Check deps (codegraph registration + verify tools), detect & confirm `test`/`lint`/`typecheck`/`smoke`, scaffold `.scrum/`. Migrates a pre-0.5 layout. |
| `/up:plan <task>` | Break the task into an ordered list of small (≤3pt) steps with file contracts → `plan.json`. Offers a deep multi-planner pass for big/ambiguous tasks. |
| `/up:run [all\|<id>]` | Drive the plan test-first: lock → implement → review → gate → close. `all` runs autonomously, pausing only at boundaries. |
| `/up:status [abort\|split\|add-file\|red\|done]` | Show the plan + active lock, or recover/override. |

## Agents

| Agent | Role | Model |
|---|---|---|
| `step-planner` | Read-only; codegraph-grounded decomposition into small (≤3pt) steps. | opus |
| `implementer` | Red → green → refactor inside the locked contract, per-criterion. | opus |
| `navigator` | Read-only review; the single gate. Logical+Flow+Comments always, polish lenses scale with step size. | opus |

## What it enforces (hooks)

- **plan-guard** — while a plan has unfinished steps and no step is locked, blocks edits to **source**
  files (docs/config/tests pass) — so you work *through* the decomposition, not around it.
- **bash-guard** — blocks shell commands that write source around the other guards (`echo >`,
  `sed -i`, `tee`, heredocs); applies the same plan/scope/TDD decision an edit would get.
- **scope-guard** — blocks edits to files outside the locked step's contract.
- **tdd-guard** — blocks source edits until a failing test is observed (`mark-red`); the close gate
  (`check-tdd`) additionally refuses to close until every acceptance criterion has its own red test.
- **done-gate** — runs the verify set in parallel (120s/check); a step cannot close on a red gate.
- **lean-inject** — injects the lean ladder into every session (wherever `.scrum/` exists); the
  ladder also carries the shared-team comment rule, so that doctrine is discoverable too. The lean
  layer is adapted from [ponytail](https://github.com/DietrichGebert/ponytail) (MIT).

No plan and no active step ⇒ all guards are inert, so ad-hoc work and projects that don't use
ultrapower are unaffected. The lean ladder is the exception — it's injected wherever `.scrum/` exists.

## Install

Ultrapower's planning and review agents use the **codegraph** MCP server (code intelligence: impact
analysis, reuse, grounding). Install it first, then the plugin.

**1. MCP server** (once per machine):
```bash
claude mcp add codegraph -- codegraph serve --mcp
```

**2. The plugin:**
```bash
claude plugin marketplace add mthanhlm/ultrapower
claude plugin install up@ultrapower
```
**Restart Claude Code** so the commands, agents, and hooks register.

**3. In each project**, run `/up:init` once.

## State (`.scrum/`)

Per-project state, always local (gitignored):
- `config.json` — the verify commands.
- `plan.json` — the ordered list of steps for the current task (stored as JSON, not a fragile table).
- `current-story.json` — the active locked step (file contract + per-criterion red set), present only
  while a step is in flight.

It is found by walking up from the working directory, so the hooks work from any subdirectory.

## Develop

The plugin's own logic (state helpers + hooks) is tested:
```bash
python3 -m pytest tests -q
ruff check .
```

## Updating

```bash
claude plugin marketplace update ultrapower
claude plugin update up@ultrapower
```
…then restart Claude Code.
