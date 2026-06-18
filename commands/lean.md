---
description: Set the lean ladder's intensity (lite/full/ultra/off). Always-on; the level persists per project.
argument-hint: "lite | full | ultra | off"
allowed-tools: Bash, Read, Edit
---

Set how hard the **lean ladder** (`lean/ladder.md`) pushes on this project. Lean is always-on: the
ladder is injected every session at the active intensity, recorded as `lean_mode` in
`.scrum/config.json`. Sub-command from `$ARGUMENTS` (default `full`):

- **lite** — build what's asked, but name the lazier alternative in one line. You pick.
- **full** — the ladder enforced: YAGNI → stdlib → native → installed dep → one line → minimum. Default.
- **ultra** — YAGNI extremist. Deletion before addition. Challenge the requirement, ship the one-liner.
- **off** — lean disabled; the ladder is not injected.

Typing `/up:lean <level>` is caught by the `lean-mode` hook, which writes `lean_mode` to
`.scrum/config.json` and re-states the ladder at the new level. Confirm the resulting level back to
the user in one line; if `lean_mode` is not yet updated (e.g. hooks disabled), set it in
`.scrum/config.json` yourself. This only changes intensity — do not touch code.

Resolution at session start: `UP_LEAN_MODE` env var > `.scrum/config.json` `lean_mode` > `full`.

The lean layer is adapted from [ponytail](https://github.com/DietrichGebert/ponytail) (MIT).
