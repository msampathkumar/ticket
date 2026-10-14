---
id: tic-fr6j
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: task
priority: 3
assignee: scion-agent
parent: tic-xv7i
tags: [webui, core]
---
# Web UI: single source of truth for blocked/ready state

tk_cli.py L198-210 recomputes blocked state separately from tk ready/blocked; they can drift.

## Acceptance Criteria

- [ ] Web UI blocked/ready lanes match tk ready and tk blocked for the same repo


## Notes

**2026-10-14T20:04:07Z**

Compared semantics: core ready/blocked only consider open/in_progress tickets; a dep blocks unless its status is exactly 'closed' (missing IDs and 'done' block); IDs matched exactly (tk dep stores resolved full IDs). Web UI matched all except it also flagged closed (non-active) tickets as blocked. Decision: align Python logic (one-line status guard) rather than shelling out: no extra subprocesses or text parsing per /api/tickets call, already O(n). Adding parity scenario.

**2026-10-14T20:06:18Z**

PR opened: https://github.com/msampathkumar/ticket/pull/24. make test 262/262, ruff pass; parity scenario fails on old logic. Perf 500 tickets: get_all_tickets 195ms vs +290ms for tk ready+blocked subprocesses.

**2026-10-14T20:08:11Z**

Coordinator: reviewed and squash-merged PR #24. CI green. Only open/in_progress tickets can be blocked, as in core; parity scenario added.
