---
description: Start a story (brief + codegraph grounding + lock the file contract) or add one to the backlog.
argument-hint: "start <id|description> | add <description>"
allowed-tools: Bash, Read, Glob, Grep, Edit, Write, AskUserQuestion, Agent
---

Drive one backlog story. Requires `.scrum/config.json` (`/up:init`). Sub-command from
`$ARGUMENTS`: `start` (default) or `add`.

## start <id | description>

1. **Resolve the story.** If an id is given, read it from `.scrum/sprint.md`; otherwise treat
   the text as a new story title. Refuse to start a second story while
   `.scrum/current-story.json` exists — finish it with `/up:done` first.

2. **Plan via the story-planner.** Invoke the `story-planner` agent with the story title and its
   acceptance criteria. It grounds in codegraph (impact + reuse) and returns a BRIEF:
   What / You'll receive / Files touched [new|edit] / Affected sites / Out of scope / Verify,
   plus a proposed point estimate.

3. **Confirm with the user.** Present the brief verbatim. The user approves or adjusts scope,
   files, and the estimate. Do not edit any code yet. Iterate until approved.

4. **Debate plan review.** Invoke the `debate` agent with the BRIEF from step 2 and the proposed
   file contract. It returns `VERDICT: proceed | revise-plan` and `FINDINGS:` severity-tagged across
   six lenses. If the verdict is `revise-plan` or any `blocker` findings are open, show the
   findings to the user, revise the brief or scope together, then re-invoke the `debate` agent until
   the verdict is `proceed`. Only once `proceed` is returned advance to step 5.

5. **Lock the contract** with the approved file list:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" lock \
     --id <id> --title '<title>' --points <n> \
     --file <path> [--file <path> ...] \
     --acceptance '<criterion>' [--acceptance ...] \
     --out '<out-of-scope item>'
   ```
   `--file` paths are resolved relative to the repo root (or absolute); they are safe to pass from any subdirectory.
   This writes `.scrum/current-story.json`. From now the scope-guard hook blocks edits outside
   `--file`, and the TDD guard blocks source edits until a failing test is observed.

6. **Mark the story `in-progress`** in `.scrum/sprint.md`, then hand off: implement test-first
   (the implementer agent runs red → green → refactor) and run `/up:done` when the work is ready.

## add <description>

Append a one-line story to `.scrum/backlog.md` (ID, title, blank points/acceptance). Quick
capture only — no planning. Suggest `/up:sprint plan` to estimate and schedule it later.
