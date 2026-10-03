#!/usr/bin/env bash
#
# Drives terminal recording for the ticket (tk) demo GIF.
# Showcases core CLI functionality: init, create, dep, ready, blocked,
# dep tree, start, add-note, and close.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
export PATH="$ROOT_DIR:$PATH"

DEMO_DIR="$(mktemp -d /tmp/tk-demo-XXXXXX)"
cd "$DEMO_DIR"
git init -q -b main
git config user.name "Demo User"
git config user.email "demo@example.com"

cleanup() {
  rm -rf "$DEMO_DIR"
}
trap cleanup EXIT

esc=$'\033'
r="${esc}[0m"
c_comment="${esc}[93m" # Bright yellow for comments

PROMPT="${esc}[1;34m➜${r}  ${esc}[35mtk-demo${r} ${esc}[34mgit:(${esc}[32mmain${esc}[34m)${r} "

TYPE_DELAY=0.02
AFTER_CMD=1.4
AFTER_NOTE=1.0

type_out() {
  printf '%s' "$1" | while IFS= read -r -n1 ch; do
    printf '%s' "$ch"
    sleep "$TYPE_DELAY"
  done
}

run() {
  printf '%s' "$PROMPT"
  type_out "$*"
  printf '\n'
  sleep 0.25
  eval "$*"
  printf '\n'
  sleep "$AFTER_CMD"
}

note() {
  printf '%s' "$PROMPT"
  printf '%s' "$c_comment"
  type_out "# $*"
  printf '%s\n' "$r"
  sleep "$AFTER_NOTE"
}

clear 2>/dev/null || true

note "tk: minimal, dependency-aware task tracker. Built to scale agentic workflows."
run "tk init"

note "Create tasks with priorities, types, and tags"
printf '%s' "$PROMPT"
type_out "tk create 'Design SQLite schema' -p 1 -t task --tags backend,db"
printf '\n'
ID_DB=$(ticket create "Design SQLite schema" -p 1 -t task --tags backend,db)
echo "Created: $ID_DB"
printf '\n'
sleep "$AFTER_CMD"

printf '%s' "$PROMPT"
type_out "tk create 'Build REST API endpoints' -p 2 -t feature --tags api"
printf '\n'
ID_API=$(ticket create "Build REST API endpoints" -p 2 -t feature --tags api)
echo "Created: $ID_API"
printf '\n'
sleep "$AFTER_CMD"

note "Declare dependencies: API endpoints depend on Database schema"
run "tk dep $ID_API $ID_DB"

note "Inspect the dependency graph tree"
run "tk dep tree $ID_API"

note "Check actionable tasks -- only unblocked tasks appear in ready queue"
run "tk ready"

note "Inspect blocked tasks waiting on prerequisites"
run "tk blocked"

note "Claim the ready task and document findings"
run "tk start $ID_DB"
run "tk add-note $ID_DB 'Selected WAL mode for concurrent reads'"

note "Close the task -- automatically unblocks downstream dependents!"
run "tk close $ID_DB"

note "Verify ready queue -- API endpoint task is now automatically unblocked!"
run "tk ready"

note "Pure POSIX Bash, zero databases, 100% Git versioned. Enjoy tk!"
sleep 1.5
