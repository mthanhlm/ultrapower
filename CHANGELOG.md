# Changelog

All notable changes to Ultrapower are documented here.

## 1.1.1 — CodeGraph readiness via injected script (replaces the hook)

### Changed
- **Replaced the `SessionStart` hook with a dynamic-context-injected script.** The
  router skill (`ultrapower:run`) runs `skills/run/scripts/codegraph-ensure.sh` via
  dynamic context injection every time it loads, so the **current** repo is indexed
  on entry without depending on a session hook firing. Same behavior: add
  `.codegraph/` to `.gitignore` and `codegraph init` when the repo has no index;
  idempotent and fail-open (no-op when already indexed, not a git repo, or the
  `codegraph` CLI is absent).

### Removed
- `hooks/` (the 1.1.0 `SessionStart` hook) — it didn't reliably fire; the injected
  script replaces it.

## 1.1.0 — Guaranteed CodeGraph readiness + entry-name fix

### Added
- **`SessionStart` hook** (`hooks/codegraph-init.sh`, wired via `hooks/hooks.json`)
  that guarantees the current repo is CodeGraph-indexed: on session start it adds
  `.codegraph/` to `.gitignore` and runs `codegraph init` when the repo has no
  index. Idempotent and fail-open — skips when the `codegraph` CLI is absent, the
  directory isn't a git repo, or the index already exists, so it never blocks
  session start.

### Changed
- **CodeGraph readiness is decided from the filesystem at the current repo root**
  (`git rev-parse --show-toplevel` + `<root>/.codegraph/`), not from whether MCP
  queries return data — a same-named sibling repo (or an MCP server launched outside
  the tree) could otherwise answer for the wrong codebase and mask a missing index.
  MCP queries are pinned with `projectPath: <root>`.
- First-use init ensures `.codegraph/` is in `.gitignore` (the `codegraph init` CLI
  does not add it); `ultrapower:implement` runs `codegraph sync` once after
  finalizing a diff so the index reflects the change.

### Fixed
- **Entry skill realigned to `run`.** The router shipped as `skills/ultrapower`
  (`/ultrapower:ultrapower`), diverging from the documented 1.0.0 design
  (`skills/run`, `/ultrapower:run`). Renamed back to `skills/run`, so the namespaced
  command is `/ultrapower:run`; the bare `/ultrapower` wrapper is unaffected.

## 1.0.0 — Router + on-demand specialists (breaking)

Full rebuild around a single public entry point with hidden, model-invocable
specialist capabilities.

### Breaking
- **Plugin renamed `up` → `ultrapower`.** Commands/skills move from `/up:*` to
  `/ultrapower:*`. Existing installs of `up` must be uninstalled and `ultrapower`
  installed. The single public entry is now **`/ultrapower:run <request>`**.
- Removed the previous per-phase command surface (`/up:go`, `/up:status`, and the
  earlier TDD/decomposition commands).

### Added
- **Router** (`skills/run`) that classifies intent and routes to specialists.
- **On-demand specialists** (hidden from the `/` menu, model-invocable):
  `implement`, `explore`, `document`, `plan`, `review`, `codegraph`.
- **Shared references** loaded on demand: challenge, comments, verify, safety,
  codegraph, persistence, and a specialist entry contract.
- **CodeGraph integration** with separate MCP/CLI detection, explore-first tool
  use, first-use local indexing, watcher-aware refresh, and an honest fallback.
- Strict source-code **comment policy** with a final comment pass on every change.
- Minimal, versioned **active-task persistence** (`.ultrapower/active.md`) with a
  working-tree baseline; read-only status; honest resume limits.
- `LICENSE`, this changelog, a structural/release `scripts/validate.py`, and an
  `evals/` routing-and-behavior suite.

### Changed
- `review` runs **isolated and read-only** (forked context, edit tools disabled);
  the separate reviewer subagent was removed — one review source of truth.
- **`explore` and `review` both run isolated and read-only (a forked Explore
  agent).** A read-only specialist's `disallowed-tools` therefore no longer leaks
  into the parent turn, so a combined request can investigate first and still
  implement/document afterwards in the same turn.
- CodeGraph guidance: default to `codegraph_explore` for broad context; the
  narrower MCP tools are **capability-detected** (they may or may not be exposed,
  depending on the installed version/config) and never assumed; CLI subcommand
  names (e.g. `codegraph query`) are kept distinct from MCP tool names.
- Challenge policy: waits on **unresolved** material user-owned decisions instead
  of guessing; an **explicit** public/consumed-contract change proceeds with a brief
  impact note rather than a confirmation checkpoint.

### Fixed
- **Combined `explore → implement`/`document` flows.** An inline read-only
  `explore` step previously left its edit-tool restriction active for the rest of
  the turn, so a following implement/document step was silently denied writes;
  isolating `explore` in a forked context resolves it. Guarded by a permanent
  regression (`evals/run.sh` `combined_ei`, validator `context: fork` check).

### Removed
- The custom Bash guard hook — Claude Code's native permission system is used instead.

## 0.7.x and earlier — `up`
The previous plugin (`up`): a TDD/XP/scrum-style decomposition framework. Replaced
wholesale by 1.0.0; not carried forward.
