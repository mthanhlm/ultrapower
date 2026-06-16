---
description: Tutor you to mastery — a read-only tutor drills you over a story's diff, a file/area, the whole project, or a topic, then saves what you learn to .scrum/tutored.md (deduped).
argument-hint: "<story-id | path | \"topic\" | project>"
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion, Agent
---

Tutor the human to **truly understand** something — and remember it. Drives the read-only `teacher`
agent to build a mastery checklist, runs the lesson interactively, and saves what is learned to
`.scrum/tutored.md` (deduped, tagged by source) so nothing is taught twice.

## 1. Resolve the target + source-tag from `$ARGUMENTS`

- a **story id** (`S<n>`) or its **diff** → teach *what you just built*; source-tag = the story id.
- a **file or area** path → teach that code; source-tag = `project`.
- a quoted **"topic"** (free text) → teach that concept as it lives in this repo; source-tag = `project`.
- **`project`** → teach the whole project's architecture; source-tag = `project`.
- **no target** (or `pending`) → work the **pending queue**: read `## Pending` in `.scrum/tutored.md`,
  show what's waiting, and tutor the next story (oldest first); source-tag = that story id.

## 2. Skip what's already mastered

Read `.scrum/tutored.md`. Anything already recorded under this source-tag is mastered — say so and
do **not** re-teach it. This is the "don't duplicate" guarantee.

## 3. Build the plan — the `teacher` agent

Invoke the `teacher` agent with the resolved target. Read-only, it grounds in the code and returns a
**CHECKLIST** of problem / solution / impact items, each with the *why*, edge cases, and a quiz
question. Drop any checklist item already in `tutored.md` for this source before teaching.

## 4. Teach interactively — to mastery, not to lecture

Work the checklist **one item at a time**; do **not** advance until the current item is demonstrated:

- **Restate-first.** Ask the user to restate their current understanding before you fill any gaps.
- **Fill the gaps** from there; offer **eli5 / eli14 / eli-intern** on request, and show code or walk
  the debugger when it helps.
- **Quiz with AskUserQuestion** — open-ended or multiple-choice. Shuffle which option is correct and
  do **not** reveal the answer until after the user submits. Drill the *why*, not just the *what*.
- When the item is demonstrated, **persist it** (step 5) and move to the next.

Do **not** end the session until **every** checklist item is mastered.

## 5. Persist what was learned (deduped)

As each item is mastered, save it — never hand-edit the file:

```
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" record-learning \
  --source <story-id|project> --topic '<concept>' --note '<one-line takeaway>'
```

The writer dedupes by `(source, topic)`, so re-running `/up:tutor` never duplicates an entry in
`.scrum/tutored.md`.

## 6. Wrap up

When a queued story is fully mastered, clear it from the queue:
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" tutor-pending --remove <id>`.
Summarise what was mastered and now lives in `tutored.md`, note anything still **pending**, and
suggest the next target if the user wants to go deeper.
