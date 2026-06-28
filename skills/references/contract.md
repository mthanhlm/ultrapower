# Specialist entry contract

Apply this when you were invoked **directly** (a natural-language request selected
you) rather than by the Ultrapower router — so nothing the router would have done
is skipped. (All paths below are bundled with this plugin under `references/`,
beside this file.)

- Respect current user instructions and `CLAUDE.md`.
- Decide **read-only vs file-changing**. Before any file write, apply
  [repository safety](safety.md): inspect the working tree, preserve unrelated
  work, never auto commit/push/branch/reset/etc.
- If the task needs **structural understanding** of the repo and the CodeGraph
  index isn't ready, ensure it via the `ultrapower:codegraph` capability, or fall
  back to search — see [codegraph policy](codegraph.md). Skip for trivial/local or
  non-repo work.
- Load only the shared references this task actually needs (don't pre-load them).
- Don't create persistent state unless it has real resume value
  ([persistence](persistence.md)).
- Challenge material problems and **wait** on genuine user-owned decisions
  ([challenge](challenge.md)); never stall on reversible ones, never guess a
  product decision.
- Verify proportionally to the outcome ([verification](verify.md)); for code
  changes, run the final [comment pass](comments.md).
- Return a concise result.
