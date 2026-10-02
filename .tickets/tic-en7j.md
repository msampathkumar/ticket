---
id: tic-en7j
status: closed
deps: []
links: []
created: 2026-10-01T14:18:07Z
type: feature
priority: 1
assignee: Sampath Kumar
parent: tic-822k
tags: []
---
# Limit SCION working tasks to 10 per project

Limit the number of active SCION working tasks to 10 per project. Once 10 tasks are working in a project, queue remaining ready tasks and only dispatch another after 1 task finishes (enters `waiting-for-review` or `closed`).

## Design

- Update `watcher.max_concurrent_per_project` default to `10` (and `watcher.max_concurrent` default >= `10`) in `plugins/scion-taskforce/tk_scion_taskforce/config.py`, `scion-taskforce.yaml`, and `SCION-TASKFORCE-SPEC.md`.
- Ensure `dispatch_ticket` and `reconcile_once` count active working tasks (`status: in_progress` with `taskforce` tag and not `waiting-for-review`) per project so at most 10 tasks are claimed/working per project at any time, and only claim a ticket when `provider.spawn` succeeds (or count `in_progress` `taskforce` tickets toward the 10-task cap).
- When 1 working task completes (`waiting-for-review` or `closed`), dispatch the next ready ticket in the queue.

## Acceptance Criteria

1. Default `max_concurrent_per_project` is `10`.
2. At most 10 SCION working tasks are active (`in_progress` with `taskforce` tag) concurrently per project.
3. Only after 1 working task finishes (`waiting-for-review` or `closed`) is the next ready ticket picked up.

## Notes

**2026-10-01T14:45:57Z**

Implemented: watcher.max_concurrent_per_project default 10 (global 10); reconciler counts running workers per project and dispatches the next opted-in ready ticket as soon as one finishes. Covered by BDD scenario 'At most N working tasks per project'.
