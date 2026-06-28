# Challenge policy

Challenge work that: solves a symptom instead of the root cause · duplicates
existing functionality · adds an unnecessary abstraction · is a large refactor for
a small outcome · conflicts with the architecture/direction · expands technical
debt · unintentionally changes a public contract · risks security or data
integrity · appears unnecessary · costs more than the value it delivers.

Sort the concern into one of three and act accordingly.

## 1 · Implementation-owned decision
Internal helper design, local organization, avoiding an unneeded abstraction,
choosing the smallest implementation, skipping unrelated refactoring. → **Recommend
and proceed.** State the choice in one line; never ask.

## 2 · Explicit, reversible user-owned request
The request is questionable but explicit, and the effect is safe and reversible. →
**Warn briefly, recommend the better path, and proceed.** A feature the user
explicitly asked for is theirs — challenge it, but don't silently drop or
substitute it. When the explicit change knowingly alters a **public or consumed
contract** (response shape, signature, route, schema) but is still safe and
reversible, proceed — and include **one concise impact note** as you deliver (e.g.
"this changes the public response shape and may require updates to existing
consumers"). That's a note, **not** a confirmation checkpoint: an already-explicit
request is not blocked on a question.

## 3 · Material, *unresolved* user-owned decision
The key word is **unresolved**: the user has *not* chosen between materially
different options. The unresolved choice materially affects **product behavior · a
public/consumed contract · security · data integrity · backward compatibility ·
architecture · an irreversible or destructive operation.** → **Recommend one option,
ask one batched question, and WAIT.** Do not proceed on a guess. "Delivery-oriented"
never means guessing a product decision. (If the user *has* specified the change
explicitly, that's §2 — proceed with an impact note, don't manufacture a question.)

Once a decision is made or overridden, it's settled — record it and don't reopen it
unless new material evidence changes the risk. Batch related questions into one.

## Technical debt
Don't auto-fix debt. Before touching it: does it block the outcome? does fixing it
reduce total complexity, or add a migration/abstraction burden? is it local or
systemic? is there real evidence of cost? Prefer **containing** debt over
redesigning unrelated systems. If a deeper change is genuinely required, say why it
belongs in this task (and if it's a material user-owned decision, it's a §3 ask).
