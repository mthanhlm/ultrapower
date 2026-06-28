# Ultrapower

A **codebase companion** for Claude Code. Not a code-only bot: it answers project
questions, writes docs, and changes code — on real, messy, evolving codebases — and
it **pushes back when a request is unreasonable or debt-prone, before a line is
written.** Ceremony scales to blast radius, never to line count.

It was built around three real failures it exists to prevent:

- **Wrong-layer debt** — e.g. a planner reaching straight into the DB instead of the
  sanctioned tool layer. → The **architecture guard** denies that edit at authoring
  time, naming the cheaper correct option.
- **The over-decomposition tax** — 30 minutes for 5 lines because everything got
  quartered. → Work is **sized by CodeGraph blast radius**; trivial changes ship in
  one pass.
- **Skill sprawl** — many skills, never used. → **One router** (`ultrapower:run`)
  dispatches a small, fixed roster.

## What's inside

| Piece | What it does |
|---|---|
| **Hooks** | `SessionStart` ensures the CodeGraph index exists, keeps `.codegraph` gitignored, and injects a project-memory summary. `UserPromptSubmit` primes code-intent prompts with the necessity ladder + active invariants (and surfaces the previous turn's note). `PreToolUse` is the **architecture guard** (denies block-invariant violations). `PostToolUse` enqueues changes; `Stop` runs the debounced `codegraph sync`, reminds you of impacted tests (`codegraph affected`), and re-scans the changed files against the invariants (layer-2 guard that catches what the live guard missed). |
| **Skills** | `run` (router) → `explore` · `plan` · `implement` · `review` · `document` · `codegraph`. |
| **Command** | `/ultrapower <request>` routes through `run`. |
| **Memory** | TOML under `.ultrapower/memory/` (committed): `codebase.toml` (architecture + invariants), `ledger.toml` (done/doing/next), `decisions.toml` (ADRs incl. rejected). |

## Requirements

- The **CodeGraph** CLI on `PATH` (`codegraph`). Without it everything still works —
  structural queries degrade to Grep/Read.
- `python3` (stdlib only; used by hooks to parse JSON/TOML).

## Install

```bash
# via a marketplace that includes this plugin, then in Claude Code:
/plugin install ultrapower
```

First run on a repo: open Claude Code there and run `/ultrapower capture the
architecture` — the `codegraph` skill drafts `.ultrapower/memory/codebase.toml`
(including the **invariants** that power the guard) and asks you to confirm before
saving. Commit `.ultrapower/memory/`.

## Defining an invariant (this is what powers the guard)

In `.ultrapower/memory/codebase.toml`:

```toml
[[invariant]]
id               = "db-only-via-mcp"
rule             = "DB access only via the centralized tool layer; no direct DB driver"
applies_to_paths = ["internal/**"]
forbid_imports   = ["database/sql", "github.com/jackc/pgx*"]
exempt_paths     = ["internal/mcp/db/**"]
severity         = "block"   # block = edit denied; warn = user asked
```

Now any edit under `internal/**` (except the exempt layer) that adds one of those
imports is **denied** with a reason — the wrong-layer mistake is caught before it
lands. Knowingly need an exception? Record an ADR in `decisions.toml` and add the
path to `exempt_paths`.

## Config

- `ULTRAPOWER_CODEGRAPH=off` — disable the CodeGraph lifecycle hooks entirely.
- `CLAUDE_PROJECT_DIR` — used to locate the project root (Claude Code sets it).

## Notes

- `.codegraph/` and `.ultrapower/state/` are gitignored automatically; only
  `.ultrapower/memory/` is committed.
- Hooks never abort your session: any tool failure degrades gracefully and exits 0.
- Telemetry (gitignored, under `.ultrapower/state/`): `activity.log` records guard
  decisions and per-turn sync/affected/violation counts; `usage.log` records which
  specialist the router picked — so a never-used skill can be spotted and removed.
