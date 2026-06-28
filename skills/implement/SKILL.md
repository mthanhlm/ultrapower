---
name: implement
description: >-
  Ultrapower specialist (router-invoked) that CHANGES code to a finished, verified
  state: implement a feature, fix a bug, refactor, debug-and-fix, upgrade a
  dependency, or complete unfinished work. Owns the whole outcome — inspect,
  change, verify, self-review, comment cleanup, concise report.
user-invocable: false
---

# Implement

Change code to a finished, verified state and report concisely. You own the whole
outcome; you don't hand back a scaffold.

If you were invoked **directly** (not via the router), first apply the
[entry contract](../references/contract.md).

## 1 · Size it, and check for resume
- **Trivial** (typo, one-line fix, small local config): minimal inspection, make
  the change, run a focused check, one-line report. No persistent spec.
- **Normal** (a bug fix or small feature): concise outcome + acceptance in the
  conversation; implement and verify in one flow.
- **Risky / cross-module / cross-session** (data, security/auth, public contract,
  concurrency, critical logic, migration): write explicit scope, non-goals,
  acceptance, and verification; persist active task state if resume value is real
  ([persistence](../references/persistence.md)).

If the request is to **resume or continue** prior/unfinished work, first reconcile
any `.ultrapower/active.md` against the current repo/branch/baseline
([persistence](../references/persistence.md)) before changing code — don't
implement against a mismatched or stale task.

## 2 · Safety pre-check (always, even trivial)
Load and apply [repository safety](../references/safety.md) before editing — the
full policy lives there. Additionally check the **target files** for existing user
edits so you don't clobber them, and respect protected/generated/vendor paths and
`CLAUDE.md`. Preserve unrelated work; run no git state-changing command without an
explicit request.

## 3 · Ground in the code, then challenge
Use the cheapest reliable tool ([codegraph policy](../references/codegraph.md)):
CodeGraph (`codegraph_explore`) for structural/cross-module questions; text search
for strings, errors, config; focused reads for specific files. Reach for blast-radius
analysis only when the impact is genuinely uncertain or cross-module.

Then challenge before building ([challenge](../references/challenge.md)): root
cause over symptom, reuse over duplication, smallest coherent solution.
Warn-and-continue on reversible choices; on a **material user-owned** decision,
ask one batched question and wait — don't guess.

## 4 · Implement the smallest coherent solution
Match the surrounding style and idiom. Reuse an existing helper before adding one.
No speculative abstraction, no drive-by refactor of code you weren't asked to
touch, no fixing unrelated debt (note it instead). Remove only what your change
orphaned.

## 5 · Comments — default to none
Per [comment policy](../references/comments.md): default to no new comment, match
the repo's existing style, and add one only for something the code can't express.
After editing, run the policy's **final comment pass** over the diff to strip
narration, AI-sounding, stale, or restating comments.

## 6 · Verify proportionally, with real evidence
Per [verification](../references/verify.md): pick the fastest reliable check and
run it; report the exact command and observed result. A behavior change must be
exercised. Add a test only when it gives real regression value.

**Baseline:** when a relevant check is cheap, run it (or reproduce the bug)
**before** editing and record the result; fix; run the same check after. If you
didn't capture a baseline, **don't** reset/stash/overwrite user work to create one
— use focused evidence (unchanged code paths, prior output, CI) and state
uncertainty rather than asserting a failure is pre-existing.

On failure: first decide whether it's caused by **your** change (vs the baseline)
— if pre-existing/unrelated, note it and don't chase it. Otherwise don't repeat
the same fix: re-examine the root-cause hypothesis, gather a little new evidence,
try a meaningfully different approach, re-verify. Stop only at a genuine blocker
(required user decision, missing credential/service, an unobtainable or
decision-bearing dependency, permission limit) — then report what's done, what
remains, the blocker (with evidence), and the next concrete action.

## 7 · Dependencies (don't over-reach)
Running a project's **declared** dependency restore is fine when it's the documented,
repo-local command and uses a frozen/locked mode (e.g. `npm ci`, `pip install -r`
with a lock, `go mod download`) — it doesn't change declarations. **Ask first**
before adding a new dependency, modifying a manifest or lockfile unexpectedly,
installing anything globally, running untrusted lifecycle scripts, or a large/
environment-wide install. If a restore is needed only to verify, say what it will do.

## 8 · Review the diff and report
Self-review the final diff (only intended changes; no debug leftovers or stray
files; unrelated work preserved). For a **risky or large** diff, delegate one
independent fresh-eyes pass to `ultrapower:review` (isolated and read-only) — the
[independent-review policy](../references/safety.md) defines what qualifies and
exactly what to hand it. Otherwise self-review is enough.

If this task persisted a `.ultrapower/active.md`, **delete it once the work is
complete and verified** (the state no longer helps) — but keep it if work remains or
a blocker stands ([persistence](../references/persistence.md)).

Report: what changed · behavior delta · verification (command + result) · residual
risk · which changes are Ultrapower's vs pre-existing. Concise.
