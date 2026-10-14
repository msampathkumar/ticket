---
id: tic-4ld5
status: closed
deps: [tic-i50j]
links: []
created: 2026-10-14T20:30:39Z
type: bug
priority: 3
assignee: Sampath Kumar
parent: tic-4294
tags: [core]
---
# Core: tk dep duplicate check uses substring match

Found in tic-i50j. cmd_dep checks for an existing dep with a substring grep, so adding tic-1 when tic-12 exists reports 'Dependency already exists'. Use an exact list-element match.

## Acceptance Criteria

- [ ] Adding a dep whose ID is a substring of an existing dep succeeds
- [ ] Behave scenario


## Notes

**2026-10-14T20:37:32Z**

PR opened: https://github.com/msampathkumar/ticket/pull/37. Exact list-element matching in dep/undep/unlink (link already exact). Behave list assertions made exact; id_resolution scenario fixed to assert full ID. 5 new scenarios fail on master, pass here. make test 280/280, shellcheck clean.

**2026-10-14T20:38:52Z**

Coordinator: reviewed and squash-merged PR #37. CI green. _list_has/_list_remove exact matching in dep, undep, unlink (undep/unlink could corrupt lists); step assertions made exact.
