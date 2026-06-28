#!/usr/bin/env bash
# ultrapower SessionStart hook: guarantee the current repo has a CodeGraph index.
# Idempotent and fail-open — exits 0 fast when codegraph is absent, this isn't a
# git repo, or the index already exists, so it never blocks a session start.

command -v codegraph >/dev/null 2>&1 || exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
[ -n "$root" ] || exit 0
[ -d "$root/.codegraph" ] && exit 0

# codegraph init does not edit .gitignore, so ignore the index ourselves.
gi="$root/.gitignore"
if [ ! -f "$gi" ] || ! grep -qE '^\.codegraph/?[[:space:]]*$' "$gi"; then
  [ -f "$gi" ] && [ -n "$(tail -c1 "$gi" 2>/dev/null)" ] && printf '\n' >>"$gi"
  printf '.codegraph/\n' >>"$gi"
fi

codegraph init "$root" >/dev/null 2>&1 || exit 0

# SessionStart stdout is added to the model's context.
echo "CodeGraph: initialized a fresh index for $root (ultrapower)."
exit 0
