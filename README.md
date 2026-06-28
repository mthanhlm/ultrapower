# Ultrapower

One lean, project-aware engineering companion for Claude Code. Bring a request in
plain language; Ultrapower works out the intent, pulls only the project evidence it
needs, routes to the right on-demand specialist, and returns one complete, useful
result — implementing, investigating, explaining, reviewing, documenting, or
planning. It challenges unnecessary or risky work before effort is wasted, and it
waits for genuinely user-owned decisions rather than guessing them — but it never
uses analysis as an excuse not to deliver.

## Using it

**One public entry point:**

```
/ultrapower:run <your request>
```

Examples:

```
/ultrapower:run fix the duplicated event publishing bug
/ultrapower:run explain how authentication works across this project
/ultrapower:run review the current diff for unnecessary complexity
/ultrapower:run write deployment docs from the actual repository
/ultrapower:run is this requested refactor actually necessary?
/ultrapower:run investigate why the event is duplicated, fix it, and document it
/ultrapower:run continue the active task
```

**`/ultrapower:run` guarantees** the router runs: intent classification,
CodeGraph readiness, combined-intent sequencing, and resume reconciliation.

You can also just describe what you want in normal conversation. Be aware this is
**best-effort**: a natural-language request may activate the router *or* select a
matching internal specialist directly (each specialist is self-contained and applies
its own safety/grounding/challenge/verification, so this is safe — it just may skip
the router's combined-intent stitching). For guaranteed orchestration, use
`/ultrapower:run`.

> **Why `/ultrapower:run` and not a bare `/ultrapower`?** Claude Code namespaces
> every marketplace-plugin command and skill as `/<plugin>:<name>`; a bare
> top-level `/ultrapower` isn't supported for plugins. There is one interface to learn.

### Optional `/ultrapower` alias (opt-in; you create it)

If you'd rather type `/ultrapower`, add a **personal standalone skill** (not the
legacy `commands/` folder). Ultrapower will **not** modify your config for you:

```sh
mkdir -p ~/.claude/skills/ultrapower
cat > ~/.claude/skills/ultrapower/SKILL.md <<'EOF'
---
name: ultrapower
description: Route any project request to Ultrapower.
argument-hint: <request>
disable-model-invocation: true
---
Use the Skill tool to invoke `ultrapower:run` with: $ARGUMENTS
EOF
```

Then `/ultrapower <request>` delegates to the router. It's your own user-level
skill; delete the folder to remove it.

## What it does (one interface, specialists behind it)

You learn one interface. Internally the router selects from on-demand specialists,
each loaded only when relevant. They're hidden from your `/` menu
(`user-invocable: false`) but remain model-invocable:

- **implement** — features, fixes, refactors, debugging, dependency upgrades,
  finishing work (inspect → change → verify → self-review → comment cleanup).
- **explore** — questions, investigations, root cause, flow tracing, impact,
  comparisons. Runs **isolated and read-only** (a forked Explore agent), so it
  returns findings without leaving a write restriction on the rest of the turn — a
  combined request can investigate first and still implement/document afterwards.
- **document** — docs returned in chat *or* written into the repo (inspects the
  code first; updates rather than duplicates).
- **plan** — plans, specs, acceptance criteria, migrations, "is this necessary?"
  (no implementation unless asked).
- **review** — reviews a diff / verifies completed work; runs **isolated and
  read-only** (a forked context, edit tools disabled). Also the independent
  fresh-eyes pass for a risky implementation — one review capability, no separate
  reviewer agent.
- **codegraph** — readies the project index (below).

## CodeGraph

Ultrapower is **CodeGraph-aware with a fallback** — it does not bundle CodeGraph.

- **Detection** — the CodeGraph **MCP** (the `mcp__codegraph__*` tools) and the
  **`codegraph` CLI** are detected **separately**; either can be present without
  the other. Ultrapower **defaults to `codegraph_explore`** (its result already
  includes relationships and blast-radius context). The narrower MCP tools
  (`codegraph_search`, `codegraph_callers`/`callees`/`impact`/`node`/`status`/`files`)
  may or may not be exposed depending on the installed CodeGraph version and MCP
  config, so Ultrapower detects which actually exist before using them and never
  hard-depends on one. (CLI subcommand names differ from MCP tool names — e.g.
  symbol search is `codegraph query`, not `codegraph search`.)
- **First-use initialization** — on the first structural request in an un-indexed
  repo, Ultrapower runs `codegraph init`, building a **local** `.codegraph/` index.
  Local, safe, and reversible, so it happens automatically (you're told once). It
  asks first if the repo is exceptionally large, the path is protected, or
  installation/credentials are needed; it skips indexing for trivial/local edits
  and non-repo requests.
- **Refresh** — `codegraph serve` runs a **file-watcher that auto-syncs**, so
  Ultrapower does **not** run `codegraph sync` routinely — only on an explicit
  staleness signal, a demonstrably stale result, a disabled watcher, or an
  unreconciled branch/worktree switch.
- **Installation** — if the CLI is absent, Ultrapower *offers* `codegraph install`
  and **asks first**. Be aware that, depending on scope, the installer is
  interactive and writes the **MCP config** *and* a **permissions auto-allow list**,
  at **global or local** scope, and the tools may need a **Claude Code
  restart/reload** to appear. Ultrapower never runs it silently or modifies
  `CLAUDE.md` / `.mcp.json` / settings on its own.
- **Privacy** — source, paths, symbols, and query content stay **local** (a local
  index + a local stdio MCP). CodeGraph may collect anonymous aggregate usage
  telemetry per its own configuration; see CodeGraph's documentation to inspect or
  disable it.
- **Remove the index** — `codegraph uninit -f`.
- **No CodeGraph?** — Ultrapower says so and uses text search + focused reads;
  work still completes.

## Comments in your code

Ultrapower defaults to **adding no new comments**. It matches your repo's existing
style and adds one only for something the code can't express (an invariant, a
security/concurrency constraint, a required workaround). Every code change ends with
a pass that keeps genuine why-comments and removes ones that merely restate code,
sound AI-generated, are stale, or mention AI/the assistant.

## Task state, resume & status

Ultrapower defaults to **no files**. For risky or cross-session work it keeps one
small `.ultrapower/active.md` (outcome, scope, acceptance, decisions, progress,
branch, baseline HEAD, and a baseline working-tree snapshot so it can tell its
changes from yours). Limitations, stated honestly:

- **One active task per worktree.**
- A **normal task with no saved state can't be reliably resumed** in a fresh
  session — Ultrapower won't reconstruct a task from your commit history.

Status questions are read-only. State is never deleted because verification failed
or you got blocked. `.ultrapower/` is transient; if you want it ignored, add these
lines yourself (Ultrapower won't edit `.gitignore`):

```
# ultrapower transient task state
.ultrapower/
```

## Safety

Ultrapower inspects the working tree before changing files and never commits,
pushes, branches, resets, restores, stashes, or cleans without an explicit
request — your unrelated changes are preserved. It respects `CLAUDE.md`, your
conventions, and protected/generated paths.

**No Bash guard hook.** Ultrapower relies on Claude Code's native permission system
rather than shipping a command filter that would run on every command, add latency,
duplicate the native prompts, and isn't a real security boundary.

## Develop / validate

- `python3 scripts/validate.py` — structural + release validator (manifests,
  frontmatter, reference path resolution, no stale `up:*`, no public specialist,
  no unsupported CodeGraph tool hard-coded, no packaged hook).
- `claude plugin validate .claude-plugin/plugin.json --strict` — official validation.
- `evals/evals.json` + `bash evals/run.sh` — behavioral E2E suite of real headless
  sessions (`bash evals/run.sh all`, or named scenarios). `[det]` scenarios assert
  hard facts (file contents, exit status, working-tree, stream events); `[beh]`
  scenarios depend on model judgement. `combined_ei` is the permanent regression
  for the explore→implement/document tool-restriction leak.

## Remove it

Uninstall/disable the plugin from the marketplace. Optionally delete any
`.ultrapower/` directory and the `.ultrapower/` lines you added to `.gitignore`, run
`codegraph uninit -f` to remove a local index, and delete
`~/.claude/skills/ultrapower/` if you created the alias.
