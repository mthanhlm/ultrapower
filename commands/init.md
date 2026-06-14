---
description: Initialise ultrapower in this project — detect verify commands, set sprint length + Definition of Done, scaffold .scrum/.
argument-hint: "[--force]"
allowed-tools: Bash, Read, Glob, Write, AskUserQuestion
---

Set up ultrapower for the current project. This is the one-time, per-project step that
teaches the plugin how to verify code here. Everything ultrapower enforces later depends
on these commands being right, so detect — do not guess — and confirm with the user.

## Steps

1. **Check for existing config**
   Run: `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" show`
   If a config already exists and `$ARGUMENTS` does not contain `--force`, show it and ask
   whether to reconfigure. Stop if the user declines.

2. **Detect candidate verify commands** by reading the repo (not from memory):
   - Node: `package.json` scripts → `test`, `lint`, `typecheck` (or `tsc --noEmit`), and a
     dev/build command that proves it boots (`smoke`).
   - Python: `pyproject.toml` / `tox.ini` / `Makefile` → `pytest`, `ruff check` / `flake8`,
     `mypy`, and a run command (`smoke`).
   - Otherwise use the ecosystem's conventional commands (go test/vet, cargo test/clippy, …).
   `smoke` must be a real run/boot check — XP's "it actually works" — not another static check.
   If you cannot find one, leave `smoke` empty rather than inventing it.

3. **Confirm with the user** via AskUserQuestion: present the detected `test`, `lint`,
   `typecheck`, and `smoke` commands and the default sprint length (7 days). Let them correct
   any value; offer "you pick" defaults where you are confident. Also ask whether `.scrum/`
   should be **`local`** (gitignored, default — recommended for most repos) or **`shared`**
   (committed, for teams that want scrum state in version control).

4. **Write config + scaffold** with the confirmed values:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" init \
     --test '<test>' --lint '<lint>' --typecheck '<typecheck>' --smoke '<smoke>' \
     --sprint-days <n> --scrum-mode <local|shared> --force
   ```
   This writes `.scrum/config.json`, creates `backlog.md`, `sprint.md`, `velocity.md`,
   `retro.md` if absent, and syncs `.gitignore` according to the chosen visibility.

5. **Bootstrap codegraph + serena for this project** (non-fatal):
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" bootstrap
   ```
   This runs `codegraph init <root>` (indexes the project) and `serena project create <root>`
   (registers the project with serena) via subprocess, then verifies the **repo-local**
   `.codegraph/` and `.serena/` directories actually exist in `<root>`. Success is that
   post-condition, not the command's exit code — so `serena project create` exiting non-zero
   on a re-init still counts as ok when `.serena/` is present, and a tool exiting 0 without
   producing its dir is reported FAIL. Both indexes stay repo-local; never the global one.
   Report per-tool ok/FAIL status. A failure does not abort init — the missing dir can be
   created later by re-running the bootstrap step. Continue to the report step regardless.

6. **Report** the written config path back, and point the user to `/up:sprint plan` as the
   next step. Commit policy follows the `scrum_visibility` you chose — `local` keeps `.scrum/`
   gitignored, `shared` commits it.
