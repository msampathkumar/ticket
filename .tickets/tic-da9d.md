---
id: tic-da9d
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: feature
priority: 2
assignee: scion-agent
parent: tic-xv7i
tags: [webui]
---
# Web UI: auto-refresh when tickets change on disk

CLI or agent changes only appear after a manual refresh. Agent-first tool should reflect changes live.

## Design

Lightweight endpoint returning max mtime/count of .tickets; frontend polls every few seconds and refetches on change (or SSE).

## Acceptance Criteria

- [ ] A tk create in a terminal appears in the open board within ~5s without clicking refresh


## Notes

**2026-10-14T19:51:46Z**

Plan: GET /api/tickets/version (stat-only count/mtime fingerprint) in main.py; app.js polls every 3s while visible, refetches on change, defers while edit/new form open or dragging. tk_cli.py untouched.

**2026-10-14T19:51:46Z**

PR opened: https://github.com/msampathkumar/ticket/pull/15. make test 227/227, ruff clean. Headless E2E: tk create visible in 1.0s, status change 2.9s, deferred during edit form and drag, no polls when hidden, no refetch when unchanged, delete reflected in 1.0s.

**2026-10-14T19:53:49Z**

Coordinator: reviewed and squash-merged PR #15. CI green. GET /api/tickets/version fingerprint, 3s visible-tab polling, deferred while editing/dragging.
