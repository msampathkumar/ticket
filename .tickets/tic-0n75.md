---
id: tic-0n75
status: closed
deps: [tic-rbze]
links: []
created: 2026-10-14T19:07:33Z
type: task
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [tests, concurrency]
---
# BDD scenario: concurrent agents claiming the same ticket

Add a black-box Behave scenario in features/: two processes claim one ticket; only one wins.

## Acceptance Criteria

- [ ] Scenario in features/ passes under make test


## Notes

**2026-10-14T19:41:22Z**

Coordinator: covered by features/ticket_claim.feature in PR #8 (2 and 8 concurrent claimers, exactly one wins).
