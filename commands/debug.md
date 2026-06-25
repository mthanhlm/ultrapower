---
description: Diagnose a hard bug or perf regression — a red-capable repro FIRST, then minimise → hypothesise → instrument → root cause → regression test. The bug-world twin of the test-first spine.
argument-hint: "<symptom>"
allowed-tools: Bash, Read, Glob, Grep, Edit, Write, AskUserQuestion, Agent
---

Diagnose a bug or performance regression with discipline, instead of guessing and patching. Use when
something is broken, throwing, failing, or slow. Best run with **no active plan** (the guards are
inert without one, so the diagnostician can build a repro and instrument freely); if a plan is in
flight, finish or clear it first.

1. **Diagnose.** Invoke the `diagnostician` agent with the symptom (`$ARGUMENTS`). It builds a tight,
   already-run, **red-capable** repro *before* forming any hypothesis (the bug-world analogue of
   red-before-green), minimises it, ranks 3–5 falsifiable hypotheses, instruments with tagged logs,
   and reports a root cause + a proposed fix + a regression-test seam. It does **not** ship the fix.

2. **Checkpoint the hypotheses.** When the diagnostician surfaces its ranked hypotheses, show them —
   you often re-rank instantly from domain knowledge ("we just changed #3"). A cheap, big checkpoint.

3. **Hard gate — no loop, no fix.** If the diagnostician could not produce a red-capable command it
   actually ran, STOP: there is no proof the bug reproduces or that a fix worked. Report what it
   tried and what it needs (an environment, a captured artifact) — do not patch on a guess.

4. **Drive the fix through the locked flow.** With a root cause and a regression seam in hand, turn
   the fix into normal ultrapower work so the guards and the navigator review apply: `/up:plan "fix
   <bug>"` with the regression test as the first acceptance criterion (the repro you built is the
   red). Don't hand-patch source here — let `/up:run` drive it test-first.

5. **Confirm cleanup.** Before declaring done, confirm all `[DEBUG-…]` instrumentation and any
   throwaway harness are removed (the diagnostician greps its tag). Record the hypothesis that held
   in the eventual fix's summary, so the next debugger learns.
