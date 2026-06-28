---
name: implement
description: Make a code change to a finished, verified state — implement a feature, fix a bug, refactor, debug-and-fix, upgrade a dependency, or complete unfinished work. Owns the whole outcome — ground, change, verify, and update memory.
---

# ultrapower: implement

## 1. Ground & necessity (skip the ceremony for a true one-liner/typo)
Work the Necessity/Reuse Ladder (see the injected reminder). For non-trivial work,
search CodeGraph for an existing helper (rung 2) and check `codebase.toml`
invariants + previously-rejected ADRs before writing. If the change would violate
a **block** invariant, STOP and propose the sanctioned path — the PreToolUse guard
will deny the edit anyway, so resolve it up front.

## 2. Size by blast radius (`codegraph_impact`/`callers`), not lines
Trivial → one pass. Standard → implement directly. Complex/wide → outline the
steps first so they're visible, then execute. Never quarter a small change.

## 3. Implement surgically
Every changed line traces to the request. Match the surrounding style and idiom.
No drive-by refactors or reformatting. Remove only the orphans your change created.

## 4. Verify — logic, not just compilation
- **Bug:** write a FAILING repro test first, then make it pass.
- **New behavior:** add tests that assert it.
- **Run the impacted tests:** `git diff --name-only | codegraph affected --stdin -q`,
  then run that subset. If it returns nothing, fall back to the project's test
  command. If there is genuinely no test infra, say so and do a runtime smoke —
  do NOT scaffold a test framework.
- Typecheck + lint the **changed files**. Compiling/typechecking alone is not "done".
Report honestly: if something failed or was skipped, say so with the real output.

## 5. Record (non-trivial only)
Update `.ultrapower/memory/ledger.toml` (status `doing`→`done`, risk, touched_files,
verified result). Add an ADR to `decisions.toml` if a real decision — or a rejected
alternative — came up. Keep entries fixed-key and short. The Stop hook syncs the
CodeGraph index automatically; you don't need to.
