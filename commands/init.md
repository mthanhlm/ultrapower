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
   any value; offer "you pick" defaults where you are confident.

4. **Write config + scaffold** with the confirmed values:
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" init \
     --test '<test>' --lint '<lint>' --typecheck '<typecheck>' --smoke '<smoke>' \
     --sprint-days <n> --force
   ```
   This writes `.scrum/config.json` and creates `backlog.md`, `sprint.md`, `velocity.md`,
   `retro.md` if absent. It never overwrites the markdown.

5. **Report** the written config path back, and point the user to `/up:sprint plan` as the
   next step. Do not commit `.scrum/` — leave staging to the user.
