---
id: tic-3p3m
status: closed
deps: []
links: []
created: 2026-10-04T23:29:14Z
type: bug
priority: 2
assignee: scion-agent
tags: [scion-taskforce]
---
# scion-taskforce: reopen should clear waiting-for-review so the worker restarts

A reopened ticket keeps its waiting-for-review tag, and is_eligible_for_dispatch rejects it, so tk reopen starts no worker. Found in the live test 2026-10-05 (tt-n0jr): the tag had to be removed by hand before reopen. Fix: on the reopen event (status closed -> open), drop waiting-for-review and dispatch; add a BDD scenario and a CHANGELOG entry.


## Notes

**2026-10-05T15:03:26Z**

Fixed: reopen clears waiting-for-review (events._decide) + BDD scenario. Live tests (test-tickets, 2 runs) pass with no manual steps; also fixed the paused-worker stall (gemini settings override in the worker template, resume-first wake).
