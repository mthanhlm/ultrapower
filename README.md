# ⚡ Ultrapower

A Claude Code plugin that fuses **Scrum** (lightweight management) with **Extreme Programming**
(quality engineering) into one enforced workflow: plan a sprint, drive each story test-first with
codegraph grounding, get a navigator review, and pass a verify-gate before anything closes.

Commands are namespaced `/up:` (the plugin is named `up`).

## The loop

```
/up:init               once per project — detect verify commands, sprint length, DoD
/up:sprint plan        guided question-bundle → crisp sprint goal + estimated backlog
/up:story start <id>   brief + codegraph impact/reuse → you approve → file contract locked
  (implement)          TDD: failing test → mark-red → minimal code → refactor
/up:done               navigator review (blocks on blockers) → done-gate (verify set) → close
/up:sprint close       record velocity → /up:retro
```

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

**1. Publish this repo** (once):

```bash
cd ultrapower
git init && git add -A && git commit -m "feat: ultrapower v0.1.0"
git branch -M main
git remote add origin https://github.com/mthanhlm/ultrapower.git
git push -u origin main
```

**2. On any machine**, add the marketplace and install:

```bash
claude plugin marketplace add mthanhlm/ultrapower
claude plugin install up@ultrapower
```

…or interactively inside Claude Code: `/plugin marketplace add mthanhlm/ultrapower` then
`/plugin install up@ultrapower`. **Restart Claude Code** so the commands and hooks register.

**3. In each project**, run `/up:init` once.

## State (`.scrum/`)

Ultrapower keeps per-project state as files under `.scrum/` — `config.json`, `sprint.md`,
`backlog.md`, `velocity.md`, `retro.md`, and the active `current-story.json`. **Commit `.scrum/`**:
it is the source of truth and travels with the repo. It is found by walking up from the working
directory, so the hooks work from any subdirectory.

## Develop

The plugin's own logic (state helpers + hooks) is tested:

```bash
python3 -m pytest tests -q
ruff check .
```
