---
name: ultrapower
description: >-
  One entry point for any engineering request about this codebase: implement,
  fix, refactor, or debug a change; investigate, explain, or trace behavior;
  answer an architecture/code question; review a diff or verify work; write
  documentation; plan or spec work; judge whether work is necessary; resume an
  active task; or any combination of these. Routes to the right specialist and
  returns one result. /ultrapower:ultrapower is the guaranteed entry.
argument-hint: <request>
---

# Ultrapower

One project-aware engineering companion. Route the request to the smallest set of
on-demand specialists, keep the work coherent, and return **one** complete result.
Deliver by default; challenge material problems and wait on genuine user-owned
decisions — but never invent a product decision and never stall on a reversible one.

## Work out the intended outcome (internally)
Determine the outcome silently. State it to the user only when the task is
ambiguous, complex/long-running, needs scope confirmation, or you're raising a
material challenge. For a trivial, obvious request, just start the work.

## Route by intent
Invoke a specialist with the Skill tool **only when it adds value**; for a trivial,
obvious request, do it directly here and report briefly.

| What the user wants | Capability |
|---|---|
| Change code — feature, bug fix, refactor, debug-and-fix, dependency upgrade, finish unfinished work | `ultrapower:implement` |
| Understand — project/architecture/code question, investigate behavior, root cause, trace flow, impact/blast radius, compare approaches (read-only analysis) | `ultrapower:explore` |
| Document — write or improve docs (in chat OR in the repo) | `ultrapower:document` |
| Plan — plan, spec, acceptance criteria, migration breakdown, strategy comparison (as a deliverable), "is this necessary?" | `ultrapower:plan` |
| Review — review a diff/implementation, verify completed work | `ultrapower:review` |
| Resume / status — continue active work, "what remains?", "is it done?" (to judge *correctness*, use `ultrapower:review`) | handle here (below) |

**Combined requests** ("investigate the bug, fix it, and document it") → run the
specialists in order (e.g. explore → implement → document), carrying findings
forward. The user gets one final result. `explore` and `review` run **isolated and
read-only** (forked), so they never restrict a later `implement`/`document` step in
the same request — but because they're isolated, pass each one enough to work from:
the investigation/review question, the intended outcome, key constraints, and the
findings form you need back.

## CodeGraph readiness (once per repo, when structure matters)
The **first** time a request needs structural understanding of this repo —
implementing **or** investigating/reviewing across code — ensure the index is
ready via `ultrapower:codegraph` (once). Skip it for trivial/local edits and for
requests not about a source tree. Don't re-check on every request. Detection,
init policy, and fallback: [codegraph policy](../references/codegraph.md).

## Before any file write
Load and apply [repository safety](../references/safety.md) (the full policy):
inspect the working tree, preserve unrelated user work, and run no git
state-changing command without an explicit request. Applies even to trivial edits.

## Challenge — deliver, but don't guess
Sort each concern per [challenge policy](../references/challenge.md) and act:
implementation-owned → take the simpler/safer option, note it, proceed; explicit &
reversible → warn briefly, proceed; **material user-owned** (see the policy for what
qualifies) → recommend one option, ask **one** batched question, and **wait** —
never guess a product decision.

## Resume & status (handle here; read-only for status)
Per [persistence & resume](../references/persistence.md): use conversation context
if present; reconcile any `.ultrapower/active.md` against the current
repo/branch/baseline; detect mismatch or staleness. For status-only questions stay
**read-only** and report only what's provable (staged vs unstaged vs untracked;
drift only if a baseline was persisted). If there's no conversation context and no
persisted state, say there's no resumable Ultrapower task — never infer one from
commits. Only one active task per worktree.

## Always
- Respect `CLAUDE.md`, repo docs, conventions, and protected/generated paths.
- Match verification to the intent ([verification](../references/verify.md)); for
  code changes run a final [comment-quality pass](../references/comments.md).
- Stay lean: load only the references the task needs, give concise progress only at
  meaningful transitions, return a short result. Don't narrate which specialist ran.
