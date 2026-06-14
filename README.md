# ⚡ Ultrapower

A Claude Code plugin that fuses **Scrum** (lightweight management) with **Extreme Programming**
(quality engineering) into one enforced workflow: plan a sprint, drive each story test-first with
codegraph grounding, get a navigator review, and pass a verify-gate before anything closes.

Commands are namespaced `/up:` (the plugin is named `up`).

## The loop

```
/up:init               once per project — detect verify commands, sprint length, DoD
/up:sprint plan        guided question-bundle → crisp sprint goal + estimated backlog
/up:story start <id>   brief + codegraph impact/reuse → you approve → debate pre-lock plan review → file contract locked
  (implement)          TDD: failing test → mark-red → minimal code → refactor
/up:done               navigator review (blocks on blockers) → done-gate (verify set) → close
/up:sprint close       record velocity → /up:retro
```

## How to use — a worked example

New to it? Here's a full pass for a small task: **"reject malformed emails on the signup form."**

**0. One-time setup** (per project)
```
/up:init
```
It scans the repo, proposes the commands it found (e.g. `pytest -q`, `ruff check .`, `mypy`, and a
run/boot smoke), and asks you to confirm. Writes `.scrum/config.json`.

**1. Plan the sprint**
```
/up:sprint plan
```
It interviews you with a few quick questions (what's the goal? what's in/out of scope? how big?),
then proposes a **sprint goal** and a short **backlog** with point estimates — e.g.
*"S1 — reject malformed emails on signup (2 pts)"*. You tweak and approve; it writes `.scrum/sprint.md`.

**2. Start a story**
```
/up:story start S1
```
The **story-planner** reads the codebase via codegraph and hands you a brief: which files it'll
touch, the approach, which existing helpers it reuses, the tests, and a verify command. You
approve → the **debate** agent runs a pre-lock plan review (five lenses, `VERDICT: proceed |
revise-plan`) → that file list is **locked** (edits outside it get blocked).

**3. Build it test-first**
- Write the failing test first — `test_rejects_malformed_email` → run it → it **fails (red)**. Required.
- *Now* source edits unlock — write the minimal validator to make it **pass (green)**.
- Refactor with the test staying green.

> If you try to edit the validator **before** a failing test exists, the **tdd-guard** stops you —
> that's the plugin keeping you honest, not a bug. (No active story? All guards are off.)

**4. Finish the story**
```
/up:done
```
The **navigator** reviews your diff against the brief (missing test? a caller you forgot? scope
creep?) and lists findings. Fix any **blockers**, then the **done-gate** runs your verify set
(tests + lint + typecheck + smoke). Green + no blockers → the story closes and the increment is tagged.

**5. Repeat & wrap up**
```
/up:sprint close     # records velocity for next sprint's planning
/up:retro            # quick 3-bullet retrospective
```

**Reach for these as needed:**
- `/up:refactor <target>` — restructure with no behavior change (checks every caller via codegraph first, keeps tests green).
- `/up:story add "<idea>"` — capture a backlog idea without planning it yet.

## Commands

| Command | What it does |
|---|---|
| `/up:init` | Detect & confirm this project's `test`/`lint`/`typecheck`/`smoke` commands, sprint length, and Definition of Done → `.scrum/config.json`. |
| `/up:sprint plan` \| `close` | Plan a sprint via a guided question-bundle; close records velocity and seeds the retro. |
| `/up:story start <id\|desc>` \| `add` | Plan + lock a story (brief, estimate, contract); or quick-add one to the backlog. |
| `/up:done` | Navigator review + done-gate, then close the active story. |
| `/up:refactor <target>` | Codegraph-impact-checked refactor with tests green throughout. |
| `/up:retro` | Short retrospective appended to `.scrum/retro.md`. |

## Agents

| Agent | Role | Model |
|---|---|---|
| `story-planner` | Read-only; codegraph-grounded brief + point estimate. | opus |
| `debate` | Read-only pre-lock plan critic — five lenses; `VERDICT: proceed \| revise-plan`. | opus |
| `implementer` | Red → green → refactor inside the locked contract. | sonnet |
| `navigator` | Read-only review; severity-tagged findings. | opus |
| `scrum-master` | Sprint planning + close facilitation; velocity. | opus |

## What it enforces (hooks)

- **scope-guard** — blocks edits to files outside the locked story contract.
- **tdd-guard** — blocks source edits until a failing test has been observed (`mark-red`).
- **comment-noise** — rejects narration comments; keeps only why-notes, TODO/FIXME, lint directives.
- **done-gate** — `/up:done` runs the configured verify set; a story cannot close on a red gate or
  with open blocker findings.

No active story ⇒ all guards are inert, so ad-hoc work and projects that don't use ultrapower are
unaffected.

## Install

Ultrapower's planning and review agents use two MCP servers — **codegraph** (code intelligence for
impact analysis + reuse) and **serena** (symbol-level edits). Install those first, then the plugin.

**1. MCP servers** (once per machine — adapt to how each tool is installed on your system):

```bash
claude mcp add codegraph -- codegraph serve --mcp
claude mcp add serena -- serena start-mcp-server --context=claude-code --project-from-cwd
```

**2. The plugin:**

```bash
claude plugin marketplace add mthanhlm/ultrapower
claude plugin install up@ultrapower
```

…or interactively: `/plugin marketplace add mthanhlm/ultrapower` then `/plugin install up@ultrapower`.
**Restart Claude Code** so the commands, agents, and hooks register.

**3. In each project**, run `/up:init` once.

## State (`.scrum/`)

Ultrapower keeps per-project state as files under `.scrum/` — `config.json`, `sprint.md`,
`backlog.md`, `velocity.md`, `retro.md`, and the active `current-story.json`. Commit policy
follows your `/up:init` choice (`scrum_visibility`) — `local` → gitignored, `shared` → committed.
It is found by walking up from the working directory, so the hooks work from any subdirectory.

## Develop

The plugin's own logic (state helpers + hooks) is tested:

```bash
python3 -m pytest tests -q
ruff check .
```

## Updating

When a new version is published, update your install:

```bash
claude plugin marketplace update ultrapower
claude plugin update up@ultrapower
```

…then restart Claude Code. A new version appears only after one is published.

