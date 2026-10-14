---
id: tic-i50j
status: closed
deps: []
links: []
created: 2026-10-14T20:25:35Z
type: feature
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [core]
---
# Core: reject dependencies that would create a cycle

Requested by user 2026-10-14. tk dep currently accepts deps that form a cycle; tk dep cycle only reports them afterwards. Reject at write time with a clear error listing the cycle path.

## Acceptance Criteria

- [ ] tk dep A B fails (exit 1) when B already depends (transitively) on A, printing the cycle
- [ ] Existing cycles still reported by tk dep cycle
- [ ] Self-dependency rejected
- [ ] Behave scenarios; SPEC 3 and dependencies.md updated


## Notes

**2026-10-14T20:30:22Z**

Decision: cycle check walks all tickets incl. closed (reopen would revive the cycle); runs after the 'already exists' check so re-adding stays a no-op. Self-dep rejected first. Bash 3.2 awk BFS, prints shortest cycle path.

**2026-10-14T20:30:22Z**

PR opened: https://github.com/msampathkumar/ticket/pull/35. make test 275/275 on bash 3.2.57, shellcheck clean. Docs: only cycle sentences in SPEC 3, dependencies.md, commands.md tk dep row. Rebased on origin/master f767ad7.

**2026-10-14T20:31:51Z**

Coordinator: reviewed and squash-merged PR #35. CI green. awk BFS over all tickets; self-deps and cycles rejected with path, exit 1, no write/hook. Follow-up: tic-4ld5.
