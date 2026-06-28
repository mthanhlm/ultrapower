---
name: plan
description: >-
  Ultrapower specialist (router-invoked) for PLANNING and SPECIFICATION: plan a
  change, write a technical spec, define acceptance criteria, break down a
  migration, compare strategies, or assess whether requested work is necessary.
  Produces the plan/spec only — does not implement unless separately asked.
user-invocable: false
---

# Plan

Produce the requested planning artifact — and only that. Do **not** implement
unless the user separately asks.

If you were invoked **directly** (not via the router), first apply the
[entry contract](../references/contract.md).

## Approach
1. Ground the plan in the actual repository
   ([codegraph policy](../references/codegraph.md)): real modules, dependencies,
   and affected areas — not a generic template.
2. Challenge first ([challenge](../references/challenge.md)): is the work
   necessary? is it over-engineered? does existing functionality already cover it?
   Distinguish **required** work from **optional** improvements and **unrelated**
   debt. For an "is this necessary?" request, give a clear verdict with evidence
   and the simpler alternative.
3. Produce proportional output: testable acceptance criteria, clear scope and
   non-goals, real dependencies and affected modules. No speculative task dumps.

## Where the plan goes
Default: return the plan **in the conversation**. A planning request does **not**
become an active implementation task.

Persist to `.ultrapower/active.md` **only if** the user asks to save it, or the
same request explicitly continues into implementation and cross-session persistence
has real value. Before writing it: apply [repository safety](../references/safety.md),
check for an existing active task, and **never silently overwrite** a different one
([persistence](../references/persistence.md)).

Verify the plan against the repo ([verification](../references/verify.md) →
planning): dependencies and modules exist, criteria are testable, scope excludes
unnecessary work.
