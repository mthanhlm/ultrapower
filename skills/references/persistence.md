# Persistence, resume & status

Default to **no files**. Most work needs none.

## When to persist
Persist active task state only when resume value is real: cross-session work · a
risky or cross-module change · complex acceptance criteria · important user
decisions that must survive. Store **one** concise file: `.ultrapower/active.md`.

## Active-task template (use this shape; omit fields that add nothing)
```
format_version: 1
task_id:                 <short slug>
repository_root:         <abs path or worktree id>
branch:                  <branch, or "(detached)" / "(non-git)">
baseline_head:           <HEAD sha when Git exists>
baseline_worktree_state: <`git status --porcelain` snapshot OR counts of pre-existing
                          staged/unstaged/untracked files — enough to tell YOUR
                          changes from what was already there; do NOT paste a full diff>
target_paths:            <files this task expects to touch, when known>
outcome:                 <one line: the result wanted>
scope:                   <what's in>
non_goals:               <what's deliberately out>
acceptance:              <checkable conditions for "done">
decisions:               <accepted decisions / overrides>
progress:                <done so far>
verification:            <what's been run + result>
remaining:               <next concrete steps>
last_updated:            <timestamp>
```
For a target file that was **already modified** before the task, record a light
fingerprint (e.g. line count or a short hash) so post-session you can tell
pre-existing edits from Ultrapower's. Keep the whole file small — not a
project-management database.

## Reading persisted state (reconcile, don't trust blindly)
Confirm `repository_root`/worktree and `branch` match; compare `baseline_head` and
`baseline_worktree_state` to now. Detect branch/worktree mismatch and obvious
staleness. Don't silently overwrite a different active task. Don't assume old state
still applies.

## Resume
Use conversation context if present. Else reconcile `.ultrapower/active.md` with the
working tree and continue from `remaining`. If neither exists, say there's no
resumable Ultrapower task — **do not** infer it from recent commits (a dirty tree
doesn't prove the changes are Ultrapower's). When a resumed task reaches completion
and its verification passes, **delete `.ultrapower/active.md`** as the final step —
the transient state no longer helps.

## Update cadence
When you stop with work remaining (a blocker or session boundary), update
`progress`, `verification`, `remaining`, and `last_updated` before stopping.

## Status (read-only)
Report only what's provable: branch · staged vs unstaged vs untracked
(`git status --porcelain`) · drift only if a baseline was persisted. Don't modify
task files or start implementation.

## Don't delete state because
verification failed · a dependency is missing · a decision is pending · an external
blocker exists · work continues later. Delete `.ultrapower/active.md` only when the
task completed (and the state no longer helps), or the user explicitly abandoned or
discarded it.

## Limitations (be honest about these)
- **One active task per worktree** (a single `active.md`). Concurrent tasks would
  need a different design.
- A **normal task with no persisted state cannot be reliably resumed** in a fresh
  session — Git changes alone are not an Ultrapower task.

## .gitignore
`.ultrapower/` holds transient task state. You may *suggest* the user ignore it,
with the comment on its own line:
```
# ultrapower transient task state
.ultrapower/
```
Never auto-add `.ultrapower/` to `.gitignore` — only *suggest* it. (CodeGraph's
`.codegraph/` index is handled separately by `ultrapower:codegraph`, which does
append it.)
