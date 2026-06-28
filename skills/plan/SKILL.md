---
name: plan
description: Plan or specify a change before building — write a technical plan/spec, define acceptance criteria, break down a migration, compare strategies, or judge whether the work is even necessary. Produces the plan only; does not implement.
---

# ultrapower: plan

## 1. Necessity / Reuse Ladder — answer in order, before proposing any new code
1. **Does this need to exist?** If no, say so and stop (YAGNI).
2. **Already in this codebase?** Search with `codegraph_search`; if a helper or
   abstraction exists, the plan is to reuse it — not rewrite.
3. Stdlib does it? 4. Native platform feature? 5. Installed dependency?
6. One line? 7. Only then: the minimum that works.

## 2. Architecture fit — be the tech lead
Before deciding *where* code goes, check with CodeGraph (`callers`/`callees`/
`impact`/`files`) and the invariants in `.ultrapower/memory/codebase.toml`:
- Right layer? Crosses a module boundary? Bypasses a centralized abstraction
  (e.g. the sanctioned data/tool layer)? Reads state that should be
  reported/event-driven instead of polled? Adds coupling/debt? Contradicts a
  recorded invariant or a previously-rejected ADR?
If anything smells like debt, surface a one-line challenge —
*"debt because X; cheaper correct option Y"* — and prefer the correct option.

## 3. Output
A short, concrete plan: what changes, which files, what to **reuse** (with paths),
the **risk tier** (trivial/standard/complex, judged by `codegraph_impact` fan-out,
not line count), and how it will be **verified**. Do not write production code in
this skill — planning only.
