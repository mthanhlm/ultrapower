#!/usr/bin/env bash
# Behavioral E2E suite for Ultrapower — real headless Claude Code sessions with the
# plugin loaded ad-hoc (no install, no config mutation).
#
#   bash evals/run.sh                 # CORE: deterministic, high-value scenarios
#   bash evals/run.sh all             # every scenario (slow; includes best-effort)
#   bash evals/run.sh combined_ei status_readonly   # named scenarios
#
# Each scenario is a real nested session, so this is deliberately slow. Needs
# `claude` on PATH and an authenticated config. Scenarios assert *observable*
# outcomes — file contents, command exit status, working-tree effects, and stream
# events (which Skill ran, whether a tool was denied) — not just response text.
#
# Two tiers:
#   [det]  deterministic — asserts hard facts; a failure is a real defect.
#   [beh]  behavioral/best-effort — depends on model judgement; a failure is a
#          signal to inspect, not necessarily a regression. Reported separately.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
PASS=0; FAIL=0; BEH_PASS=0; BEH_FAIL=0
STREAM=""
ok(){      echo "  PASS  $1"; PASS=$((PASS+1)); }
bad(){     echo "  FAIL  $1"; FAIL=$((FAIL+1)); }
beh_ok(){  echo "  beh-pass  $1"; BEH_PASS=$((BEH_PASS+1)); }
beh_bad(){ echo "  beh-FAIL  $1 (inspect; model-judgement)"; BEH_FAIL=$((BEH_FAIL+1)); }

# ---------- fixtures ----------
mkrepo(){ # $1=name [bug=1] -> path ; a node repo with a failing test + README
  local d="$WORK/$1"; rm -rf "$d"; mkdir -p "$d/src"
  cat > "$d/package.json" <<'J'
{ "name":"demo","type":"module","scripts":{"test":"node test.mjs"} }
J
  cat > "$d/sum.js" <<'J'
export function sum(a, b) {
  return a - b;
}
J
  cat > "$d/src/auth.js" <<'J'
export function loginUser(name, token){ return { name, token }; }
J
  cat > "$d/src/app.js" <<'J'
import { loginUser } from './auth.js';
export function handleLogin(req){ return loginUser(req.name, req.token); }
export function adminLogin(req){ return loginUser('admin', req.token); }
J
  cat > "$d/test.mjs" <<'J'
import { sum } from './sum.js';
import assert from 'node:assert';
assert.strictEqual(sum(2, 3), 5);
console.log('ok');
J
  printf '# Demo\n\nTODO: document the module.\n' > "$d/README.md"
  echo "keep me" > "$d/UNRELATED.txt"
  ( cd "$d" && git init -q && git add -A && git -c user.email=t@t -c user.name=t commit -qm init )
  echo "$d"
}

# ---------- session runner ----------
run_session(){ # $1=repo $2=prompt ; rest = extra claude args -> $STREAM
  local repo="$1" prompt="$2"; shift 2
  STREAM="$repo.stream.jsonl"   # sibling of the repo dir — NOT inside it, so it
                                # never shows up in the fixture's working tree

  ( cd "$repo" && timeout 360 claude -p "$prompt" --plugin-dir "$ROOT" \
      --output-format stream-json --verbose "$@" ) > "$STREAM" 2>&1
}

# ---------- assertions ----------
skill_invoked(){ grep -q "\"skill\": *\"ultrapower:$1\"" "$STREAM"; }            # a SKILL ran
no_perm_denied(){ ! grep -q 'has been denied' "$STREAM"; }                       # no leaked block
stream_has(){ grep -qiE "$1" "$STREAM"; }                                        # text/keyword over stream
file_has(){ grep -q "$2" "$1"; }
tree_clean(){ [ -z "$(git -C "$1" status --porcelain)" ]; }
test_green(){ ( cd "$1" && node test.mjs ) >/dev/null 2>&1; }
head_is(){ [ "$(git -C "$1" rev-parse HEAD)" = "$2" ]; }
no_git_danger(){ ! git -C "$1" reflog 2>/dev/null | grep -qiE '\b(reset|stash|clean|checkout|revert)\b'; }

# ===================== SCENARIOS =====================

# --- [det] PERMANENT combined-flow regression: explore SKILL must NOT block a later write ---
sc_combined_ei(){
  echo "### [det] combined: explore -> implement (regression for the tool-restriction leak)"
  local R; R="$(mkrepo combined_ei)"
  run_session "$R" 'Two steps in order, in one turn: (1) Use the Skill tool to invoke the ultrapower:explore specialist to investigate why `npm test` fails and report the root cause — read-only, do NOT fix. (2) After it returns, fix sum.js so the test passes, then run `npm test` to verify.' \
    --permission-mode bypassPermissions
  skill_invoked explore && ok "explore SKILL invoked (leak path exercised)" || bad "explore SKILL not invoked"
  no_perm_denied && ok "no 'has been denied' after explore (restriction did not leak)" || bad "a tool was denied after explore — LEAK"
  file_has "$R/sum.js" 'a + b' && ok "sum.js actually edited (file content asserted)" || bad "sum.js unchanged (print-only / blocked)"
  test_green "$R" && ok "npm test exits 0 after fix (exit status asserted)" || bad "test still red"
}

# --- [det] explore -> document ---
sc_combined_ed(){
  echo "### [det] combined: explore -> document"
  local R; R="$(mkrepo combined_ed)"
  run_session "$R" 'Two steps in order, in one turn: (1) Use the Skill tool to invoke the ultrapower:explore specialist to investigate what sum.js does — read-only. (2) After it returns, update README.md with a short section documenting the sum() function.' \
    --permission-mode bypassPermissions
  skill_invoked explore && ok "explore SKILL invoked" || bad "explore SKILL not invoked"
  no_perm_denied && ok "no tool denied after explore" || bad "a tool was denied after explore — LEAK"
  ! file_has "$R/README.md" 'TODO: document the module' && ok "README.md actually rewritten" || bad "README unchanged (blocked)"
  file_has "$R/README.md" 'sum' && ok "README documents sum()" || bad "README missing sum docs"
}

# --- [det] explore -> implement -> document (full chain) ---
sc_combined_eid(){
  echo "### [det] combined: explore -> implement -> document"
  local R; R="$(mkrepo combined_eid)"
  run_session "$R" 'Three steps in order, in one turn: (1) Use the Skill tool to invoke the ultrapower:explore specialist to find why `npm test` fails — read-only, do NOT fix. (2) Fix sum.js so the test passes and run `npm test`. (3) Update README.md to document the fix.' \
    --permission-mode bypassPermissions
  skill_invoked explore && ok "explore SKILL invoked" || bad "explore SKILL not invoked"
  no_perm_denied && ok "no tool denied after explore" || bad "a tool was denied after explore — LEAK"
  file_has "$R/sum.js" 'a + b' && ok "sum.js actually edited" || bad "sum.js unchanged"
  test_green "$R" && ok "npm test exits 0" || bad "test still red"
  ! file_has "$R/README.md" 'TODO: document the module' && ok "README.md actually updated" || bad "README unchanged"
}

# --- [det] explore read-only (no writes; finds callers) ---
sc_explore_readonly(){
  echo "### [det] explore: read-only, enumerates callers"
  local R; R="$(mkrepo explore_ro)"; local h; h="$(git -C "$R" rev-parse HEAD)"
  run_session "$R" '/ultrapower:run what functions call loginUser?' \
    --permission-mode bypassPermissions
  stream_has 'handleLogin' && ok "finds handleLogin caller" || bad "missed handleLogin"
  stream_has 'adminLogin'  && ok "finds adminLogin caller"  || bad "missed adminLogin"
  tree_clean "$R" && ok "read-only: working tree unchanged" || bad "explore modified the tree"
  head_is "$R" "$h" && ok "read-only: no commit" || bad "HEAD moved"
}

# --- [det] implement: fix + verify + no narration comment + preserve unrelated ---
sc_implement_fix(){
  echo "### [det] implement: fix + verify + no-comment + preserve unrelated"
  local R; R="$(mkrepo impl_fix)"
  run_session "$R" '/ultrapower:run sum(2,3) should be 5 but the test fails — fix it' \
    --permission-mode bypassPermissions
  test_green "$R" && ok "test passes after fix" || bad "test still red"
  ! file_has "$R/sum.js" '//' && ok "no narration comment added to the fix" || bad "comment added to fix"
  file_has "$R/UNRELATED.txt" 'keep me' && ok "unrelated file preserved" || bad "unrelated file lost"
}

# --- [det] plan-only: no files written ---
sc_plan_only(){
  echo "### [det] plan-only: no working-tree changes, no active.md"
  local R; R="$(mkrepo plan_only)"
  run_session "$R" '/ultrapower:run plan only (do not implement): how would you add a logout function?' \
    --permission-mode bypassPermissions
  tree_clean "$R" && ok "no working-tree changes" || bad "plan wrote to the tree"
  [ ! -f "$R/.ultrapower/active.md" ] && ok "no .ultrapower/active.md created" || bad "active.md created unasked"
}

# --- [det] document draft in chat: must NOT write files ---
sc_doc_chat(){
  echo "### [det] document: draft-in-chat does not write files"
  local R; R="$(mkrepo doc_chat)"
  run_session "$R" '/ultrapower:run draft (in chat only, do not write any file) a short overview of src/auth.js' \
    --permission-mode bypassPermissions
  tree_clean "$R" && ok "no files written for an in-chat draft" || bad "doc-in-chat wrote a file"
  stream_has 'loginUser' && ok "draft references the real symbol" || bad "draft did not reference code"
}

# --- [det] status: read-only; reports staged/unstaged/untracked; no active.md ---
sc_status_readonly(){
  echo "### [det] status: read-only and accurate about tree state"
  local R; R="$(mkrepo status_ro)"
  echo "unstaged change" >> "$R/sum.js"                 # unstaged
  echo "new staged"      >  "$R/staged.txt"; git -C "$R" add staged.txt
  echo "loose untracked" >  "$R/untracked.txt"          # untracked
  local before; before="$(git -C "$R" status --porcelain)"
  run_session "$R" '/ultrapower:run what is the status of the current work?' \
    --permission-mode bypassPermissions
  [ "$(git -C "$R" status --porcelain)" = "$before" ] && ok "read-only: tree state identical after status" || bad "status changed the tree"
  [ ! -f "$R/.ultrapower/active.md" ] && ok "status did not create active.md" || bad "status wrote active.md"
  stream_has 'staged'    && ok "mentions staged"    || beh_bad "status: did not mention 'staged'"
  stream_has 'untracked' && ok "mentions untracked" || beh_bad "status: did not mention 'untracked'"
}

# --- [det] no persisted state -> honest 'no resumable task'; no inference from commits ---
sc_status_no_state(){
  echo "### [det] resume with no state: honest 'no resumable task'"
  local R; R="$(mkrepo no_state)"
  echo "// drive-by edit" >> "$R/sum.js"     # a dirty tree that is NOT an ultrapower task
  run_session "$R" '/ultrapower:run resume the previous Ultrapower task' \
    --permission-mode bypassPermissions
  stream_has 'no (resumable|active|saved|persisted|ultrapower).{0,30}task|nothing to resume|no .{0,20}task to resume' \
    && ok "says there is no resumable Ultrapower task" || bad "did not honestly report 'no resumable task'"
  [ ! -f "$R/.ultrapower/active.md" ] && ok "did not fabricate active.md" || bad "fabricated active.md"
}

# --- [det] repository safety: preserve unrelated + staged + untracked + pre-existing target edit ---
sc_safety_preserve(){
  echo "### [det] safety: preserve unrelated/staged/untracked + pre-existing target edit; no reset/stash"
  local R; R="$(mkrepo safety)"
  local h; h="$(git -C "$R" rev-parse HEAD)"
  # unrelated modified, staged, untracked, and a PRE-EXISTING edit in the target file
  echo "DO NOT TOUCH" >> "$R/UNRELATED.txt"                       # unrelated unstaged
  echo "staged content" > "$R/STAGED.txt"; git -C "$R" add STAGED.txt
  echo "loose" > "$R/UNTRACKED.txt"                               # untracked
  # pre-existing edit in target: a marker line ABOVE the bug
  printf 'export const VERSION = "keep-me";\nexport function sum(a, b) {\n  return a - b;\n}\n' > "$R/sum.js"
  run_session "$R" '/ultrapower:run sum(2,3) should be 5 but the test fails — fix only that bug' \
    --permission-mode bypassPermissions
  file_has "$R/sum.js" 'a + b'                && ok "requested fix applied" || bad "fix not applied"
  file_has "$R/sum.js" 'keep-me'              && ok "pre-existing edit in target preserved" || bad "pre-existing target edit clobbered"
  file_has "$R/UNRELATED.txt" 'DO NOT TOUCH'  && ok "unrelated unstaged change preserved" || bad "unrelated change lost"
  file_has "$R/STAGED.txt" 'staged content'   && ok "staged file preserved" || bad "staged file lost"
  file_has "$R/UNTRACKED.txt" 'loose'         && ok "untracked file preserved" || bad "untracked file lost"
  head_is "$R" "$h"                           && ok "no commit (HEAD unchanged)" || bad "auto-committed"
  no_git_danger "$R"                          && ok "no reset/stash/clean/checkout in reflog" || bad "ran a forbidden git op"
}

# --- [det] review -> fix: review is read-only, then a fix is applied (read-only -> write transition) ---
sc_review_then_fix(){
  echo "### [det] review then fix: review read-only, later fix writes"
  local R; R="$(mkrepo review_fix)"
  run_session "$R" 'First use the Skill tool to invoke ultrapower:review on the sum.js bug (read-only, report findings). Then fix sum.js so `npm test` passes, and run it.' \
    --permission-mode bypassPermissions
  no_perm_denied && ok "no tool denied after review (review fork did not leak)" || bad "tool denied after review — LEAK"
  file_has "$R/sum.js" 'a + b' && ok "fix applied after review" || bad "fix not applied after review"
  test_green "$R" && ok "test green after review->fix" || bad "test still red"
}

# --- [beh] challenge: UNRESOLVED material decision -> recommend one + ask one + WAIT (no silent edit) ---
# The request is genuinely ambiguous: "more convenient" leaves several materially
# different public-contract options unresolved (object-by-id / paginated / fields).
sc_challenge_material(){
  echo "### [beh] challenge: UNRESOLVED material decision -> recommend one + ask one + wait"
  local R; R="$(mkrepo chal_mat)"
  cat > "$R/src/api.js" <<'J'
// listUsers is part of the public API; existing callers depend on its shape.
export function listUsers(db){ return db.users; }   // currently returns an ARRAY
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm api
  local before; before="$(cat "$R/src/api.js")"
  run_session "$R" '/ultrapower:run make the listUsers response more convenient for the frontend' \
    --permission-mode bypassPermissions
  stream_has 'recommend|suggest|option|which|would you|prefer|should I|\?' \
    && beh_ok "identifies the ambiguity and recommends + asks one question" || beh_bad "no recommendation/question surfaced"
  [ "$(cat "$R/src/api.js")" = "$before" ] \
    && beh_ok "did NOT edit the public contract before a decision" || beh_bad "changed src/api.js before the user decided"
}

# --- [beh] challenge: EXPLICIT public-contract change -> impact note, proceed, verify, no blocking question ---
# The user fully specified the change; policy §2 says warn-and-proceed, not wait.
sc_challenge_explicit_contract(){
  echo "### [beh] challenge: EXPLICIT public-contract change -> impact note + proceed + verify (no block)"
  local R; R="$(mkrepo chal_expl)"
  cat > "$R/src/api.js" <<'J'
export function listUsers(db){ return db.users; }   // public: returns an ARRAY
J
  cat > "$R/api.test.mjs" <<'J'
import { listUsers } from './src/api.js';
import assert from 'node:assert';
const out = listUsers({ users: [ {id:'a',n:1}, {id:'b',n:2} ] });
assert.ok(!Array.isArray(out), 'expected an object, not an array');
assert.strictEqual(out.a.n, 1); assert.strictEqual(out.b.n, 2);
console.log('ok');
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm api
  run_session "$R" '/ultrapower:run change listUsers to return an object keyed by user id instead of an array, update it, and verify with `node api.test.mjs`' \
    --permission-mode bypassPermissions
  stream_has 'public|consumer|compatib|breaking|response shape|existing caller' \
    && beh_ok "surfaces a public-contract impact note" || beh_bad "no impact note surfaced"
  ( cd "$R" && node api.test.mjs ) >/dev/null 2>&1 \
    && beh_ok "delivered the explicit change in one turn (verified) — no blocking question" || beh_bad "did not deliver+verify the explicit change"
}

# --- [beh] challenge: explicit reversible request -> proceed (maybe a brief note), do not block ---
sc_challenge_reversible(){
  echo "### [beh] challenge: reversible request -> proceed without blocking"
  local R; R="$(mkrepo chal_rev)"
  cat > "$R/src/util.js" <<'J'
function _fmt(x){ return String(x); }
export function label(x){ return _fmt(x); }
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm util
  run_session "$R" '/ultrapower:run rename the private local helper _fmt to formatLabel for clarity' \
    --permission-mode bypassPermissions
  file_has "$R/src/util.js" 'formatLabel' && beh_ok "applied the reversible rename" || beh_bad "did not apply a safe reversible change"
}

# --- [beh] persistence: active.md on a different branch -> detect mismatch, do not blindly resume ---
sc_persist_branch_mismatch(){
  echo "### [beh] persistence: branch mismatch is detected on resume"
  local R; R="$(mkrepo persist_bm)"
  mkdir -p "$R/.ultrapower"
  cat > "$R/.ultrapower/active.md" <<'M'
format_version: 1
task_id: add-logout
branch: feature/logout
baseline_head: 0000000000000000000000000000000000000000
outcome: add a logout() function
remaining: write logout() and its test
M
  run_session "$R" '/ultrapower:run resume the active task' \
    --permission-mode bypassPermissions
  stream_has 'branch|mismatch|different|does not match|stale|baseline' && beh_ok "flags branch/baseline mismatch" || beh_bad "resumed without flagging the mismatch"
}

# --- [beh] cross-session persistence lifecycle: session1 partial+persist, session2 resume+finish+cleanup ---
sc_persist_lifecycle(){
  echo "### [beh] persistence lifecycle: session1 persists partial work; session2 resumes, finishes, cleans up"
  local R; R="$(mkrepo persist_life)"
  cat > "$R/mathx.js" <<'J'
export function add(a, b){ return a - b; }   // BUG: should add
export function mul(a, b){ return a + b; }   // BUG: should multiply
J
  cat > "$R/mathx.test.mjs" <<'J'
import { add, mul } from './mathx.js';
import assert from 'node:assert';
assert.strictEqual(add(2, 3), 5, 'add'); assert.strictEqual(mul(2, 3), 6, 'mul');
console.log('ok');
J
  echo "keep me" > "$R/KEEP.txt"
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm seed
  local head; head="$(git -C "$R" rev-parse HEAD)"
  echo "unrelated user edit" >> "$R/KEEP.txt"   # pre-existing unrelated change to preserve across BOTH sessions

  echo "  -- SESSION 1 (fix add() only; persist remaining for cross-session resume) --"
  run_session "$R" '/ultrapower:run This is cross-session work. Fix ONLY the add() bug in mathx.js now and verify add() with node. Do NOT fix mul() yet. Persist an Ultrapower active task in .ultrapower/active.md (outcome, baseline_head, branch, progress, verification, and that mul() remains) so a later session can resume.' \
    --permission-mode bypassPermissions
  local s1=0
  if [ -f "$R/.ultrapower/active.md" ]; then ok "session1 created .ultrapower/active.md"; s1=1; else bad "session1 did not persist active.md"; fi
  ( cd "$R" && node -e "import('./mathx.js').then(m=>process.exit(m.add(2,3)===5?0:1))" ) && ok "session1 fixed add()" || bad "session1 did not fix add()"
  if [ "$s1" = 1 ]; then
    grep -qiE 'mul|remain' "$R/.ultrapower/active.md" && ok "active.md records remaining work (mul)" || bad "active.md missing remaining work"
    grep -qiE 'baseline|head|branch' "$R/.ultrapower/active.md" && ok "active.md records baseline/branch" || beh_bad "active.md lacks baseline/branch"
    grep -q "$head" "$R/.ultrapower/active.md" && beh_ok "active.md baseline_head matches the real HEAD" || beh_bad "active.md baseline_head not the real HEAD"
  fi

  echo "  -- SESSION 2 (fresh session: resume and finish) --"
  run_session "$R" '/ultrapower:run resume the active Ultrapower task and finish it; run `node mathx.test.mjs` to verify' \
    --permission-mode bypassPermissions
  ( cd "$R" && node mathx.test.mjs ) >/dev/null 2>&1 && ok "session2: full test green (add AND mul fixed)" || bad "session2: test still failing"
  file_has "$R/KEEP.txt" 'unrelated user edit' && ok "unrelated user edit preserved across both sessions" || bad "unrelated edit lost"
  head_is "$R" "$head" && ok "no auto-commit across the lifecycle (HEAD unchanged)" || bad "a session committed"
  [ ! -f "$R/.ultrapower/active.md" ] && ok "active.md cleaned up only after successful completion" || beh_bad "active.md not cleaned up after completion"
}

# --- [beh] verification-failure -> resume: a failed state survives, resumed session changes approach ---
sc_persist_verify_fail(){
  echo "### [beh] verify-fail then resume: failed state persists; resumed session corrects approach and verifies"
  local R; R="$(mkrepo persist_vf)"
  cat > "$R/parse.js" <<'J'
// parseAmount returns integer cents: "12.34" -> 1234
export function parseAmount(s){
  return parseInt(s, 10) * 100;   // BUG: parseInt stops at '.', dropping the cents
}
J
  cat > "$R/parse.test.mjs" <<'J'
import { parseAmount } from './parse.js';
import assert from 'node:assert';
assert.strictEqual(parseAmount('12.34'), 1234);
console.log('ok');
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm seed
  local head br; head="$(git -C "$R" rev-parse HEAD)"; br="$(git -C "$R" rev-parse --abbrev-ref HEAD)"
  mkdir -p "$R/.ultrapower"
  cat > "$R/.ultrapower/active.md" <<M
format_version: 1
task_id: fix-parse-amount
repository_root: $R
branch: $br
baseline_head: $head
outcome: parseAmount('12.34') must return 1234 (integer cents)
scope: parse.js parseAmount only
progress: attempted fix — multiplied parseInt(s,10) by 100; STILL WRONG
verification: FAILED — node parse.test.mjs => 1200 !== 1234 (parseInt drops the cents)
decisions: the parseInt(s,10)*100 approach cannot recover cents — do NOT reuse it
remaining: use a cents-preserving parse, e.g. Math.round(parseFloat(s)*100)
last_updated: seeded-failed-state
M
  run_session "$R" '/ultrapower:run resume the active Ultrapower task; read the recorded failure and try a DIFFERENT approach, then run `node parse.test.mjs` to verify' \
    --permission-mode bypassPermissions
  ( cd "$R" && node parse.test.mjs ) >/dev/null 2>&1 && ok "resumed session fixes parseAmount and verification passes" || bad "still failing after resume"
  ! file_has "$R/parse.js" 'parseInt(s, 10) * 100' && ok "did NOT repeat the recorded failed approach (parseInt*100)" || bad "repeated the failed approach"
  head_is "$R" "$head" && ok "no auto-commit during resume" || bad "resume committed"
}

# ===================== COMMENT POLICY (focused) =====================
# --- [det] preserve a valuable invariant/compat comment across an unrelated edit ---
sc_comment_preserve(){
  echo "### [det] comments: preserve a valuable invariant comment across a rename"
  local R; R="$(mkrepo cmt_keep)"
  cat > "$R/rate.js" <<'J'
// WINDOW_MS MUST stay 60000 to match the gateway's fixed 60s bucket, or counts drift.
const WINDOW_MS = 60000;
export function bucket(t){ return Math.floor(t / WINDOW_MS); }
export function rename_me(x){ return x; }
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm seed
  run_session "$R" '/ultrapower:run rename the function rename_me to identity (just the rename)' \
    --permission-mode bypassPermissions
  file_has "$R/rate.js" 'MUST stay 60000 to match the gateway' && ok "kept the valuable invariant comment" || bad "dropped the invariant comment"
  file_has "$R/rate.js" 'function identity' && ok "applied the requested rename" || bad "rename not applied"
}

# --- [det] a comment made inaccurate by the change is corrected or removed ---
sc_comment_stale(){
  echo "### [det] comments: a comment made stale by the change is corrected/removed"
  local R; R="$(mkrepo cmt_stale)"
  cat > "$R/clamp.js" <<'J'
// Clamps the value to a maximum of 100.
export function clamp(x){ return Math.min(x, 100); }
J
  cat > "$R/clamp.test.mjs" <<'J'
import { clamp } from './clamp.js';
import assert from 'node:assert';
assert.strictEqual(clamp(250), 200);
console.log('ok');
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm seed
  run_session "$R" '/ultrapower:run change clamp to cap at 200 instead of 100, then run `node clamp.test.mjs`' \
    --permission-mode bypassPermissions
  ( cd "$R" && node clamp.test.mjs ) >/dev/null 2>&1 && ok "behavior changed to cap at 200 (verified)" || bad "change not applied/verified"
  ! file_has "$R/clamp.js" 'maximum of 100' && ok "stale '100' comment corrected or removed" || bad "left the stale '100' comment"
}

# --- [beh] a justified WHY-comment is added for a non-obvious constraint ---
sc_comment_justified(){
  echo "### [beh] comments: a justified why-comment is added for a non-obvious constraint"
  local R; R="$(mkrepo cmt_just)"
  cat > "$R/poll.js" <<'J'
export async function poll(fetchOnce, sleep){
  // TODO: implement
}
J
  git -C "$R" add -A && git -C "$R" -c user.email=t@t -c user.name=t commit -qm seed
  run_session "$R" '/ultrapower:run implement poll(fetchOnce, sleep): loop calling await fetchOnce(); if truthy, return it; otherwise await sleep(1100) and repeat. The 1100ms delay is REQUIRED because the upstream rate limiter uses a 1-second window plus jitter and rejects faster polling.' \
    --permission-mode bypassPermissions
  grep -qiE 'rate|window|jitter|upstream|1100' "$R/poll.js" && beh_ok "added a why-comment for the 1100ms constraint" || beh_bad "no why-comment for the non-obvious constraint"
  ! grep -qiE 'claude|\bAI\b|ultrapower|as requested|TODO: implement' "$R/poll.js" && beh_ok "no AI/narration/placeholder comment left" || beh_bad "left an AI/narration/placeholder comment"
}

# --- [det] no AI/narration comment introduced on a simple fix ---
sc_comment_no_ai(){
  echo "### [det] comments: no AI/narration comment introduced on a simple fix"
  local R; R="$(mkrepo cmt_noai)"
  run_session "$R" '/ultrapower:run sum(2,3) should be 5 but the test fails — fix it' \
    --permission-mode bypassPermissions
  test_green "$R" && ok "fix verified" || bad "fix not applied"
  ! grep -qiE 'claude|\bAI\b|ultrapower|prompt|updated logic|as requested|// (loop|check|return|increment|set|add) ' "$R/sum.js" \
    && ok "no AI/narration/history comment introduced" || bad "introduced a banned comment"
}

# ===================== DISPATCH =====================
CORE=(combined_ei status_readonly status_no_state safety_preserve plan_only \
      comment_preserve comment_stale comment_no_ai)
ALL=(combined_ei combined_ed combined_eid explore_readonly implement_fix plan_only \
     doc_chat status_readonly status_no_state safety_preserve review_then_fix \
     challenge_material challenge_explicit_contract challenge_reversible \
     persist_branch_mismatch persist_lifecycle persist_verify_fail \
     comment_preserve comment_stale comment_justified comment_no_ai)

sel=("${CORE[@]}")
if [ "$#" -gt 0 ]; then
  if [ "$1" = "all" ]; then sel=("${ALL[@]}"); else sel=("$@"); fi
fi

echo "=== Ultrapower behavioral E2E — scenarios: ${sel[*]} ==="
for s in "${sel[@]}"; do echo; "sc_$s"; done

echo ""
echo "=== SUMMARY: det $PASS passed / $FAIL failed ; beh $BEH_PASS passed / $BEH_FAIL to-inspect ==="
[ "$FAIL" -eq 0 ]
