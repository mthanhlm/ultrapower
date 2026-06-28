---
name: review
description: Independent fresh-eyes review of completed work or the current diff — correctness, data flow, boundaries, security, compatibility, complexity, and maintainability. Read-only; reports findings by severity.
context: fork
agent: Explore
---

# ultrapower: review (read-only, fresh eyes)

Examine the change (`git diff`) with clean context. Ground claims in CodeGraph
(`callers`/`callees`/`impact`) — does any edit create a new edge across a boundary
the `.ultrapower/memory/codebase.toml` invariants forbid?

Check, in order of importance:
1. **Correctness / logic** — does it actually do what was asked, including edge cases?
2. **Wrong-layer / boundary bypass** — versus the recorded invariants.
3. **Tests** — is the changed behavior actually exercised? (compiling ≠ verified)
4. Security, compatibility, and needless complexity.

Report findings grouped by **severity** (high / medium / low), each with `file:line`
and a concrete fix. Do not edit anything — review only.
