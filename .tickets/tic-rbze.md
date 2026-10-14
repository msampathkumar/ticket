---
id: tic-rbze
status: closed
deps: []
links: []
created: 2026-10-14T19:07:32Z
type: feature
priority: 1
assignee: scion-agent
parent: tic-4294
tags: [core, concurrency]
---
# Atomic ticket claiming for concurrent agents

No locking today: two agents can tk start the same ticket. Needed to back the 'scale agentic workflows' claim.

## Design

mkdir-based lock (portable, atomic) around status writes; add tk start --claim [--assignee X] that fails if already in_progress by another assignee. Exit code documented in SPEC.

## Acceptance Criteria

- [ ] Two concurrent tk start --claim on one ticket: exactly one succeeds
- [ ] Stale lock handling documented
- [ ] SPEC updated


## Notes

**2026-10-14T19:38:01Z**

Plan/decisions: per-ticket mkdir lock at .tickets/.locks/<id>.lock (owner file: pid host epoch) around cmd_status and claims; stale if owner pid dead on same host or older than TK_LOCK_STALE_SECONDS (60); wait TK_LOCK_TIMEOUT (10s) then exit 4. tk start <id> --claim [--assignee X] (default git user.name, else USER) exits 3 if in_progress for another assignee; re-claim by same assignee is idempotent. Plain tk start unchanged. Concurrency scenario covers tic-0n75.

**2026-10-14T19:39:51Z**

PR opened: https://github.com/msampathkumar/ticket/pull/8. make test 227/227 pass (claim feature 10x no flakes), ruff clean. Covers tic-0n75 scenario.

**2026-10-14T19:41:22Z**

Coordinator: reviewed and squash-merged PR #8. CI green. mkdir locks + --claim (exit 3 lost claim, exit 4 lock timeout); SPEC 4.1/4.2 added. Follow-ups: tic-gthn (.locks gitignore), tic-xypv (sed escaping).
