---
description: Run a short sprint retrospective and append the notes to .scrum/retro.md.
argument-hint: ""
allowed-tools: Bash, Read, Glob, Write, Edit, AskUserQuestion, Agent
---

Capture lessons from the sprint so the next one is better. Lightweight — a few questions, then a
durable note.

1. **Start from the draft.** `/up:sprint close` already seeds a dated **DRAFT** section in
   `.scrum/retro.md`. Read it, plus `.scrum/sprint.md` and `.scrum/velocity.md` for signal
   (optionally `git log` over the sprint). If none exists (running retro standalone), seed one:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" draft-retro --sprint <n> --goal '<goal>' --committed <c> --completed <m>`.

2. **Ask the user** (AskUserQuestion, one small bundle): what went well, what slowed you down, and
   the single change to try next sprint. Offer "you pick" defaults drawn from the signal above.

3. **Fill in the draft — don't author from scratch.** Replace the seed bullets in the DRAFT
   section with the answers and delete the `DRAFT` marker. Optionally use the `scrum-master`
   agent to tighten it to Went well / Hurt / One change to try.

4. Keep it short — three bullets beat three paragraphs. Suggest `/up:sprint plan` to start the
   next sprint with that change in mind.
