# CodeGraph: detection, use, and fallback

Ultrapower is **CodeGraph-aware with a fallback** — it does not bundle CodeGraph.
It targets the **codegraph** integration: an MCP server (`codegraph serve --mcp`,
exposing `mcp__codegraph__codegraph_*` tools) backed by the `codegraph` CLI. The
index is a local `.codegraph/` directory.

## Detect MCP and CLI separately
- **MCP capability** = the `mcp__codegraph__*` tools exist this session.
- **CLI** = `command -v codegraph` (optionally `codegraph --version`).
These are independent; the bootstrap skill handles all combinations (MCP+CLI,
MCP-only, CLI-only, neither, indexed, not-indexed, old version).

## Tool surface — explore-first, capability-detected
**Default to `codegraph_explore`** because it provides broad structural context —
its result already includes source, relationships, call paths, and blast-radius
context. Narrower MCP tools (`codegraph_search`, `codegraph_callers`,
`codegraph_callees`, `codegraph_impact`, `codegraph_node`, `codegraph_status`,
`codegraph_files`) **may or may not be available** depending on the installed
CodeGraph version and MCP configuration. **Detect their actual availability**
(they appear as `mcp__codegraph__*` tools this session) before using them, and
**never hard-depend** on one — fall back to `codegraph_explore`.

MCP tool names are **not** CLI commands. When only the CLI is available, the
matching subcommands are `codegraph query <search>` (symbol search — the CLI
subcommand is `query`, not `search`), `codegraph callers`, `codegraph callees`,
`codegraph impact`, `codegraph files`, and `codegraph status`. There is no
`codegraph explore` or `codegraph node` CLI subcommand — use the MCP tool, or a
broader `codegraph query`, for those.

## When to USE the graph
Structural questions: definitions · references · callers/callees · type/interface
relationships · implementations · module dependencies · shared contracts ·
cross-module flows · blast radius / impact · similar implementations · architectural
boundaries.

## When NOT to
A known local typo · an exact error string · config values · plain documentation
text · a single known file · dynamic/runtime strings the graph can't represent.
Don't run impact analysis just because a symbol has two references — only when
blast radius is meaningfully uncertain or cross-module.

## Cheapest reliable tool, in order
1. current user/project instructions → 2. context you already have → 3. CodeGraph
(`codegraph_explore`) for structure → 4. native language intelligence → 5. targeted
text search → 6. focused file reads → 7. broad repo search only if needed. Don't
write Python/shell search scripts when these answer it; don't re-query the same
thing; summarize, don't paste large graph output.

## Initialization & refresh
Handled once per repo by `ultrapower:codegraph`: `codegraph init` when available and
un-indexed (local, safe, reversible — no confirmation unless huge / protected path /
needs install/credentials). The MCP server's **file-watcher auto-syncs** on change
and reconciles on connect, so don't run `codegraph sync` routinely — only on an
explicit staleness signal, a demonstrably-stale result, a disabled watcher
(`--no-watch`), or an unreconciled branch/worktree switch.

## Installation (only ever offered, never run silently)
If the CLI is absent, you may offer `codegraph install`. Be precise: it is
**interactive by default** and, depending on scope, writes the **MCP server config**
*and* a **permissions auto-allow list**, at **global or local** scope, for one or
more agents — and the tools may need a Claude Code **restart/reload** to appear.
Before offering: detect whether the CLI already exists; explain what it changes and
ask which scope. Don't run the interactive installer inside a non-interactive shell
(it hangs). Either hand the user the exact command (e.g. `codegraph install -t
claude-code -l local`), preview with `codegraph install --print-config claude-code`
(no writes), or run it non-interactively only after the user picks a scope. Never
silently modify `CLAUDE.md`, `.mcp.json`, settings, or global config.

## Privacy
Per the supported CodeGraph integration, source code, file paths, symbols, and query
content stay **local** (the `.codegraph/` index and a local stdio MCP server).
CodeGraph may collect anonymous aggregate usage telemetry per its own configuration;
consult CodeGraph's own documentation to inspect or disable it. Remove the local
index with `codegraph uninit -f`.

## Fallback (no CodeGraph)
If the `mcp__codegraph__*` tools don't exist and no CLI is available, detect it
explicitly, don't pretend the graph was used, use text search + focused reads
(approximate impact by searching references), and complete the request. An
un-indexed repo is *not* the same as no CodeGraph — that's a one-time `codegraph
init`.
