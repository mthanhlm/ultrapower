# Source-code comment policy

**Default: add no new comment.** Preserve the codebase's existing comment style and
density. Add a source-code comment only when it records something the code itself
cannot express.

## Do NOT add comments that
restate the next line · explain obvious control flow · narrate implementation
steps · describe simple assignments · repeat a variable/function name · announce
that logic was added/changed/improved/fixed · explain standard language/framework
behavior · give generic educational explanations · mention Claude, AI, Ultrapower,
the prompt, or the implementation process · preserve temporary reasoning · add
headings inside ordinary functions · sprinkle TODO/NOTE/IMPORTANT/HACK · duplicate
what names, types, tests, or docs already say · exist only to make generated code
look documented · sound unlike the comments already in the repo.

Examples that must normally NOT be added:
`// Loop through all users` · `// Check if the user exists` · `// Return the
result` · `// Updated logic for the new feature` · `// Use a map for better
performance` · `// This function handles authentication`

## A comment MAY explain
why a surprising implementation is necessary · a non-obvious business rule · an
invariant · a security constraint · a concurrency/ordering requirement · a
compatibility requirement · a protocol/external-spec requirement · a documented
external-system workaround · an intentional performance trade-off · a limitation a
maintainer might wrongly remove · public-API documentation required by repo
convention.

Prefer fixing **names, types, function boundaries, structure, tests, or docs** over
adding a comment. When an existing comment becomes inaccurate, update it if still
useful, or remove it if redundant/misleading.

## Final comment pass (every code change)
Keep comments that explain a genuine why/invariant/constraint (see above). Then
scan the diff and remove: comments that restate code · AI-sounding comments ·
temporary reasoning · stale comments · excessive docstrings · comments in a
different tone from the repo · comments mentioning implementation history or
AI/Claude/Ultrapower/prompts.
