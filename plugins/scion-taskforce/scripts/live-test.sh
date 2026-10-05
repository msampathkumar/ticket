#!/usr/bin/env bash
# Black-box live test for tk scion-taskforce (real Scion workers). Run inside a tk project that has
# `tk scion-taskforce init` done and the doc-writer skill installed.
#   Test 1: poem -> rename note -> close -> reopen with a new note -> 4-section poem
#   Test 2: role:doc-writer review ticket -> review.md, cloud.md untouched
set -u
TIMEOUT=${TIMEOUT:-240}
OUT="test-runs/$(date +%Y%m%d-%H%M%S)"
fail() { echo "FAIL: $*"; exit 1; }
has_tag() { tk show "$1" | grep -E '^tags:' | grep -q "$2"; }
# wait_for <label> <shell condition>: syncs every 5 s; prints seconds taken
wait_for() {
  local label=$1 cond=$2 t0=$SECONDS
  while (( SECONDS - t0 < TIMEOUT )); do
    tk scion-taskforce sync >/dev/null 2>&1
    if eval "$cond"; then echo "  ok  $label ($((SECONDS - t0))s)"; return 0; fi
    sleep 5
  done
  fail "$label (no result after ${TIMEOUT}s)"
}
[ -e 123123.md ] || [ -e cloud.md ] || [ -e review.md ] && fail "move 123123.md/cloud.md/review.md away first"
export TK_HOOKS_SYNC=1

echo "Test 1"
A=$(tk create "Write a poem to 123123.md" -d "Write a short, original poem (8-12 lines) about clouds and save it as 123123.md in the project root." --tags taskforce)
wait_for "poem written and reported" "[ -f 123123.md ] && has_tag $A waiting-for-review"
tk add-note "$A" "Please rename 123123.md to cloud.md (keep the content unchanged), then report back." >/dev/null
wait_for "renamed after note to paused worker" "[ -f cloud.md ] && [ ! -e 123123.md ] && has_tag $A waiting-for-review"
tk close "$A" >/dev/null
tk add-note "$A" "Reopened: please replace cloud.md with a longer poem in 4 sections (with section headings), fun to read; keep it in cloud.md, then report." >/dev/null
tk reopen "$A" >/dev/null
has_tag "$A" waiting-for-review && fail "reopen kept waiting-for-review"
wait_for "4-section poem after reopen" "[ \$(grep -c '^## ' cloud.md) -ge 4 ] && has_tag $A waiting-for-review"

echo "Test 2"
SUM=$(shasum cloud.md)
B=$(tk create "Review the cloud.md poem" -d "Read cloud.md and create review.md with concrete suggestions to improve the poem for better social acceptance (inclusive, clear, broadly appealing tone). Do not edit cloud.md." --tags taskforce,role:doc-writer)
tk scion-taskforce brief "$B" | grep -q "tk-scion-doc-writer/SKILL.md" || fail "brief does not name the doc-writer skill"
wait_for "review.md written and reported" "[ -s review.md ] && has_tag $B waiting-for-review"
[ "$(shasum cloud.md)" = "$SUM" ] || fail "cloud.md changed during review"

tk close "$A" >/dev/null; tk close "$B" >/dev/null
mkdir -p "$OUT" && mv cloud.md review.md "$OUT/"
echo "PASS ($A, $B; outputs in $OUT)"
