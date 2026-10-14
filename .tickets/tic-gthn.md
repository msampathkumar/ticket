---
id: tic-gthn
status: closed
deps: [tic-rbze]
links: []
created: 2026-10-14T19:40:25Z
type: chore
priority: 3
assignee: scion-agent
parent: tic-4294
tags: [core, concurrency]
---
# Core: keep .tickets/.locks out of git

Follow-up from PR #8 (tic-rbze). Lock dirs under .tickets/.locks/ could be committed if a commit happens while a lock is held. Have tk init write .tickets/.gitignore with '.locks/' (and '.hooks/hooks.log'?) or document it.

## Acceptance Criteria

- [ ] Fresh tk init ignores .tickets/.locks/
- [ ] Existing repos documented


## Notes

**2026-10-14T19:55:35Z**

Plan: tk init appends missing '.locks/' and '.hooks/hooks.log' to .tickets/.gitignore (idempotent, keeps existing content; scion-taskforce plugin already ignores hooks.log in .hooks/.gitignore and appends to .tickets/.gitignore the same way). Lock root also writes a self-ignoring .locks/.gitignore ('*') so repos initialized earlier are covered without re-running init. SPEC 4.2 Git bullet.

**2026-10-14T19:57:11Z**

PR opened: https://github.com/msampathkumar/ticket/pull/19. make test 242/242, shellcheck + ruff clean.

**2026-10-14T20:01:48Z**

Coordinator: reviewed and squash-merged PR #19. CI green. tk init appends .locks/ and .hooks/hooks.log to .tickets/.gitignore; lock dir self-ignores.
