---
name: codegraph
description: >-
  Ultrapower specialist (router-invoked): makes the project's CodeGraph index
  ready for structural analysis — detects the CodeGraph MCP capability and the CLI
  separately, checks whether the repo is indexed, and initializes the local index
  when safe. Runs once when structural understanding will help.
user-invocable: false
---

# CodeGraph bootstrap

Make the project's CodeGraph index ready, then return so the original request can
continue. Do this **once** per repo per session, only when structural understanding
will help. Full policy: [codegraph policy](../references/codegraph.md).

## Detect (MCP and CLI are separate things)
- **MCP capability:** present iff `mcp__codegraph__*` tools exist this session.
  **Default to `codegraph_explore`** for broad structural context. The narrower
  tools (`codegraph_search`, `codegraph_callers`, `codegraph_callees`,
  `codegraph_impact`, `codegraph_node`, `codegraph_status`, `codegraph_files`)
  **may or may not be present** depending on the installed CodeGraph version and
  MCP config — detect which `mcp__codegraph__*` tools actually exist before using
  them and never hard-depend on one; otherwise rely on `codegraph_explore`.
- **CLI:** present iff `command -v codegraph` succeeds (optionally `codegraph
  --version`). The CLI may be absent even when the MCP works (it can be launched
  via an absolute path, `npx`, or a wrapper), and vice-versa. CLI subcommand names
  differ from MCP tool names — symbol search is `codegraph query` (not `codegraph
  search`); `callers`/`callees`/`impact`/`files`/`status` exist, but there is no
  `codegraph explore`/`node`.

Handle the states distinctly — MCP+CLI / MCP-only / CLI-only / neither /
indexed / not-indexed / old-incompatible version — don't collapse them to
"installed vs not".

## Is this repo indexed? (check THIS repo's root, deterministically)
Resolve the repo root with `git rev-parse --show-toplevel`, then check for
`<root>/.codegraph/` **on the filesystem** — that directory's presence at the
current root is the authoritative signal. With the CLI you can confirm via
`codegraph status --json`: `{"initialized":false}` = not indexed,
`{"initialized":true,...}` = indexed — but also verify its reported `projectPath`
**equals `<root>`**. Do **not** infer "indexed" from MCP queries merely returning
data: a different repo with the **same folder name** (or an MCP server launched
outside this tree) can answer for the wrong codebase. When you query MCP, pin it to
this tree (`projectPath: <root>`). (The `codegraph_status` MCP tool *erroring* on a
missing db means **not initialized**, not "unavailable" — don't fall back to grep
on it.)

## First-use initialization (local, safe → no confirmation)
On entry, if CodeGraph is available and `<root>/.codegraph/` is **absent**:
1. **Ensure it's ignored** — if `<root>/.gitignore` has no `.codegraph/` line,
   append one. `codegraph init` does **not** edit `.gitignore`, so the fresh index
   would otherwise show up as untracked.
2. **Initialize** — run `codegraph init <root>` (builds the local `.codegraph/`
   index; reversible with `codegraph uninit -f`).
Tell the user one line: "Indexing this project for the first time…", then continue
the original request. **Ask first** only if the repo is exceptionally large / the
operation has meaningful resource impact, the index path is protected, or it would
need installation/credentials. Skip only for non-repo requests.

## Refresh — sync after writes; the watcher covers the rest
`codegraph serve` runs a file-watcher that **auto-syncs** on changes and reconciles
on connect. After Ultrapower **changes files** (e.g. `ultrapower:implement`), run
`codegraph sync` once so the index reflects the edits without waiting on the watcher.
Otherwise don't sync every session — only when status shows pending/stale data, a
query result is demonstrably behind the files, the watcher is disabled (`--no-watch`,
slow `/mnt` filesystems), or a branch/worktree switch wasn't reconciled.

## If CodeGraph isn't available
Don't pretend it was used. Offer to install it (see policy — it changes config and
asks for scope, so **ask first**), and meanwhile fall back to text search + focused
reads. Complete the request regardless.
