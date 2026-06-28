# Repository safety & sources of truth

## Before modifying files (every file-changing task, including trivial)
- Inspect the working tree: **unstaged** changes, **staged** changes, **untracked**
  files, and the current branch (`git status --porcelain`, `git diff`,
  `git diff --staged`). In a non-Git project, note that and skip Git-specific checks.
- Check the target files for existing user edits; preserve unrelated work.
- Identify generated, vendor, protected, or sensitive paths and leave them alone
  unless the task is explicitly about them.

## Never do automatically
commit · push · create or delete branches · stash · reset · restore · checkout
paths · clean untracked files · amend. Do these only when the user explicitly asks
and it is safe. Observe with status/diff; distinguish staged / unstaged /
untracked. Don't claim the repo "changed since X" unless a baseline exists.

## At completion
Distinguish Ultrapower's changes from pre-existing user changes in the report.

## Sources of truth (respect, don't duplicate)
Current user instructions · `CLAUDE.md` · repo documentation · existing
architecture and domain terminology · project verification commands ·
formatting/style conventions · existing documentation locations. Don't create an
Ultrapower memory file that duplicates `CLAUDE.md` or maintained docs. Persist
durable project context only when the user asks, no better source exists, the
information is stable, and it will materially help future work.

## Independent review
There is **one** review capability: the `ultrapower:review` skill, which runs in an
isolated, read-only forked context (the single source of truth — no separate
reviewer agent). Delegate to it for an explicit "review this" request, and as the
final fresh-eyes pass on a risky implementation: security-sensitive,
data-integrity, public-contract, concurrency, critical business logic, a meaningful
cross-module change, or a large production diff. Give it only: the intended outcome,
acceptance criteria, constraints, the relevant diff/files, verification evidence,
known risks, and accepted decisions. One review pass, no debate loops. If it can't
run, do a focused self-review instead.
