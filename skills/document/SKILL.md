---
name: document
description: >-
  Ultrapower specialist (router-invoked) for DOCUMENTATION: write or improve
  READMEs, architecture overviews, deployment and API guides, and module docs —
  either returned in chat or written into the repo. Inspects the real
  implementation first, reuses existing terminology, and updates existing docs
  instead of duplicating.
user-invocable: false
---

# Document

Produce documentation that matches how the project actually works.

If you were invoked **directly** (not via the router), first apply the
[entry contract](../references/contract.md).

## Pick the mode (infer; ask only if the destination materially changes the result)
- **Draft / explanation in chat** ("explain how X works", "draft a deployment
  guide") → return the documentation in the conversation. **Don't modify files**;
  no working-tree pre-check needed.
- **Repository doc update** ("update the README", "document this module in the
  docs") → write into the repo. First apply [repository safety](../references/safety.md)
  (inspect the working tree, preserve unrelated work, never auto-commit), find and
  **update the correct existing document** rather than duplicating, and report the
  changed path.

## Either mode
1. Identify the **audience** and **purpose** (maintainer? operator? API consumer?).
2. Reuse the project's terminology and existing locations
   ([sources of truth](../references/safety.md)).
3. **Inspect the real implementation before describing it**
   ([codegraph policy](../references/codegraph.md) — `codegraph_explore` or focused
   reads). Don't document assumptions as facts; distinguish current behavior from
   intended design where it matters.
4. Write concisely for the audience.

## Verify ([verification](../references/verify.md) → documentation)
Documented behavior matches the code; run commands and check examples and links
where practical; terminology consistent. If you include source-code snippets
destined for the repo, apply the [comment policy](../references/comments.md).
