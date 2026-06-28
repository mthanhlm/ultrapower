#!/usr/bin/env bash
# ultrapower: ensure the CURRENT git repo has a CodeGraph index.
# Run by the ultrapower skills on entry (replaces the old SessionStart hook).
# Idempotent and fail-open; prints a single status line the caller can relay.
#
# Usage: codegraph-ensure.sh [start-dir]   (defaults to $PWD)

start="${1:-$PWD}"

if ! command -v codegraph >/dev/null 2>&1; then
  echo "codegraph: CLI not found — skipping (install codegraph to enable indexing)."
  exit 0
fi

root=$(git -C "$start" rev-parse --show-toplevel 2>/dev/null) || {
  echo "codegraph: '$start' is not a git repo — skipping."
  exit 0
}
[ -n "$root" ] || { echo "codegraph: no repo root — skipping."; exit 0; }

if [ -d "$root/.codegraph" ]; then
  echo "codegraph: already indexed ($root/.codegraph)."
  exit 0
fi

# codegraph init does not edit .gitignore, so ignore the index ourselves.
gi="$root/.gitignore"
if [ ! -f "$gi" ] || ! grep -qE '^\.codegraph/?[[:space:]]*$' "$gi"; then
  [ -f "$gi" ] && [ -n "$(tail -c1 "$gi" 2>/dev/null)" ] && printf '\n' >>"$gi"
  printf '.codegraph/\n' >>"$gi"
fi

if codegraph init "$root" >/dev/null 2>&1; then
  echo "codegraph: initialized a fresh index at $root/.codegraph (added .codegraph/ to .gitignore)."
else
  echo "codegraph: init failed at $root — continuing without an index."
fi
exit 0
