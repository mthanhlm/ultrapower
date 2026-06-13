---
description: Run a short sprint retrospective and append the notes to .scrum/retro.md.
argument-hint: ""
allowed-tools: Bash, Read, Glob, Write, Edit, AskUserQuestion, Agent
---

Capture lessons from the sprint so the next one is better. Lightweight — a few questions, then a
durable note.

1. **Gather signal.** Read `.scrum/sprint.md` and `.scrum/velocity.md`; optionally `git log` over
   the sprint window. Note shipped vs. committed.

2. **Ask the user** (AskUserQuestion, one small bundle): what went well, what slowed you down, and
   the single change to try next sprint. Offer "you pick" defaults drawn from the signal above.

3. **Synthesize.** Optionally use the `scrum-master` agent to turn the answers + velocity into a
   tight retro: Went well / Hurt / One change to try.

4. **Append** a dated section to `.scrum/retro.md` (newest first). Keep it short — three bullets
   beat three paragraphs. Suggest `/up:sprint plan` to start the next sprint with that change in
   mind.
