# Verification by intent

Match verification to the requested outcome. "Verify" is **not** a synonym for
"write tests". Report the exact command(s) run and what you observed; never declare
completion on "this should work" when a practical check exists.

**Implementation** — existing tests · focused regression test · type check ·
compile/build · lint/static analysis · run the behavior · reproduce-then-confirm-
fixed · API/schema validation · focused manual UI check. A behavior change must be
exercised. Add a test only when it gives real regression value — never to mirror
the implementation or satisfy a process.

**Analysis & investigation** — claims grounded in code/evidence; relevant
alternatives considered; facts vs assumptions separated; referenced paths and
relationships exist; uncertainty stated honestly.

**Project questions** — the answer points to the correct files/symbols/config/docs/
graph relationships; behavior is not invented; current implementation is
distinguished from intended design where needed.

**Documentation** — documented behavior matches the code; commands and examples
checked where practical; links and file references correct; terminology
consistent; existing docs updated rather than duplicated.

**Planning & specs** — the plan reflects the real repo; dependencies and affected
modules are real; acceptance criteria are testable; scope/non-goals clear;
speculative work excluded.

**Review** — findings tie to real code and impact; severity is justified; relevant
contracts and call paths considered; no generic, style-only, or fabricated
findings.
