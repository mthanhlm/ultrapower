---
description: Initialise ultrapower in this project — check deps, detect verify commands, scaffold .scrum/. One-time per project.
argument-hint: "[--force]"
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion, mcp__codegraph__codegraph_explore
---

Set up ultrapower for the current project. This is the one-time, per-project step that teaches the
plugin how to verify code here. Everything the plugin enforces later depends on these commands being
right, so detect — do not guess — and confirm with the user.

## Steps

1. **Check dependencies first (folded-in doctor).** Run:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" doctor`
   It probes whether the **codegraph** MCP server is *registered with Claude Code*
   (via `claude mcp list`, not a bare PATH check) plus any verify tools. Present the output as-is.
   codegraph is REQUIRED: `doctor` now exits non-zero if codegraph is `[MISSING]`, so init cannot
   proceed. Show the printed `claude mcp add …` line, tell the user to run it manually (never run
   installers yourself), and stop until codegraph is registered.

2. **Migrate an old layout (if present).** If any of `sprint.md`, `velocity.md`, `backlog.md`,
   `retro.md`, `tutored.md` exist under `.scrum/`, this repo used a pre-0.5 version. Print their
   contents **once** so nothing is silently lost, tell the user they are superseded by `plan.json`
   (which `/up:plan` writes) and can be deleted, and leave the old files on disk — do not delete user
   data. The new flow is `/up:plan` → `/up:run` → `/up:status`.

3. **Check for existing config.** Run `scrum_state.py show`. If a config exists and `$ARGUMENTS`
   lacks `--force`, show it and ask whether to reconfigure; stop if the user declines.

4. **Detect candidate verify commands** by reading the repo (not from memory):
   - Node: `package.json` scripts → `test`, `lint`, `typecheck` (or `tsc --noEmit`), and a dev/build
     command that proves it boots (`smoke`).
   - Python: `pyproject.toml` / `tox.ini` / `Makefile` → `pytest`, `ruff check` / `flake8`, `mypy`,
     and a run command (`smoke`).
   - Otherwise the ecosystem's conventional commands (go test/vet, cargo test/clippy, …).
   `smoke` must be a real run/boot check — XP's "it actually works" — **not** another static check,
   and **not** a watch/serve command (it must exit; the done-gate times each check out at 120s).

5. **Confirm with the user** via AskUserQuestion: present the detected `test`/`lint`/`typecheck`/
   `smoke`. Let them correct any value. If `smoke` or `typecheck` came back empty, say so plainly —
   "the gate will NOT prove it boots / typechecks; pick a command or accept the gap" — rather than
   writing a silent "". `.scrum/` is always local (gitignored); there is no visibility choice.

6. **Write config + scaffold:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" init \
     --test '<test>' --lint '<lint>' --typecheck '<typecheck>' --smoke '<smoke>' --force
   ```
   This writes `.scrum/config.json` and gitignores `.scrum/`, `.codegraph/`.

7. **Bootstrap codegraph for this project** (non-fatal):
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" bootstrap`
   Indexes the project (`codegraph init`), then verifies the repo-local `.codegraph/` dir exists —
   success is that post-condition, not exit code. Report per-tool ok/FAIL; a failure does not abort
   init (re-run later). The index stays repo-local.

8. **Seed a project glossary (optional).** A `CONTEXT.md` glossary lets the planner, navigator, and
   implementer speak your domain's words (and think in fewer tokens). **Skip a near-empty or throwaway
   repo** — a glossary guessed before there's a domain is noise. If the repo has real code, **offer**
   it (AskUserQuestion, easy to skip): draft 3–8 genuinely project-specific terms from the README and
   main modules (one `codegraph_explore` over the core flows helps) — recurring domain nouns, names
   that mean something special here, words used inconsistently. **Skip generic programming words.**
   Present the draft, and **interview only where a term is unclear or ambiguous** (one question at a
   time, with your recommended definition — "you say 'account': Customer or User?"); ask for any term
   the code can't reveal. Write the confirmed terms to `CONTEXT.md` at the repo root
   (`git rev-parse --show-toplevel`): bold term + a 1–2 sentence definition of what it IS + an
   optional `_Avoid:_` synonym list — glossary only, no implementation detail or spec. On skip, note
   they can add `CONTEXT.md` by hand anytime (agents read it whenever it appears) or re-run
   `/up:init --force`.

9. **Report** the config path and point the user to `/up:plan <task>` as the next step.
