---
name: codegraph
description: Make the project ready for structural work and capture how it works — ensure the CodeGraph index exists, and bootstrap/maintain the .ultrapower TOML memory (architecture, modules, invariants, decisions). Run on a new repo or when asked to capture the architecture / set up guardrails.
---

# ultrapower: codegraph — index + memory onboarding

## Index
The SessionStart hook already runs `codegraph status -j` and `codegraph init` when
the index is missing, and keeps `.codegraph` gitignored. If the index looks stale
or locked, run `codegraph sync -q`, or `codegraph unlock` then `codegraph status -j`.

## Bootstrap project memory (first run / "capture the architecture")
1. If `.ultrapower/memory/` does not exist, create it by copying the templates from
   `${CLAUDE_PLUGIN_ROOT}/memory-templates/` → `.ultrapower/memory/`
   (`codebase.toml`, `ledger.toml`, `decisions.toml`).
2. Draft `codebase.toml` grounded in real structure (`codegraph_files`,
   `codegraph_explore`): the architecture summary, the main modules (id / path /
   role), and especially the **invariants** — the layering rules the team actually
   relies on (e.g. "DB access only via the sanctioned tool layer"), each with
   `applies_to_paths`, `forbid_imports`, `exempt_paths`, and `severity`
   (`block` = the guard denies a violating edit; `warn` = it asks).
3. **Do not invent invariants.** Present the draft and ask the user to confirm or
   correct it before saving — these drive the hard PreToolUse guard, so wrong ones
   cause false blocks and missing ones let debt through.

Commit `.ultrapower/memory/` — it is intent that travels with the branch. `.codegraph`
stays gitignored (regenerable structural truth).
