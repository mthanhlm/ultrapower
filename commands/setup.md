---
description: Check that the MCP servers and verify tools required by ultrapower are installed. Reports present/missing and provides install guidance — never auto-installs.
argument-hint: ""
allowed-tools: Bash, Read
---

Run the doctor check to confirm all dependencies are in place before using ultrapower.

This command checks and guides only — it never auto-installs anything. Any `claude mcp add`
lines it prints are for you to run manually.

1. **Run the doctor subcommand:**
   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/scrum_state.py" doctor
   ```
   Present the full output to the user exactly as printed.

2. **Interpret the report:**
   - `[OK]` — the tool is on `PATH` and ready.
   - `[MISSING]` — the tool was not found. For MCP deps (`codegraph`, `serena`), the doctor
     prints the exact `claude mcp add …` command to run manually. Verify tools (e.g. `pytest`,
     `ruff`) must be installed via the project's normal environment setup.

3. **Guidance only.** Do not run `claude mcp add`, `pip install`, or any installer on the
   user's behalf. Show the printed guidance and stop. The user decides what to install.
