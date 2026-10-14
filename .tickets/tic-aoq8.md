---
id: tic-aoq8
status: closed
deps: [tic-q9lz]
links: []
created: 2026-10-14T19:11:34Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-xv7i
tags: [webui, core]
---
# Atomic, consistent writes to projects.json

tk_cli.py L54-65 rewrites ~/.local/state/tk/projects.json in place; core register_global_project (python3) writes the same file. Concurrent writes can corrupt it.

## Design

Write temp file + os.replace; align format with core (see tic-q9lz which may rewrite the core side).

## Acceptance Criteria

- [ ] Writes are atomic in both writers
- [ ] Both writers produce the same schema


## Notes

**2026-10-14T19:49:07Z**

Plan: match core register_global_project: read via shared helper (dict or legacy list, strings only), write {"projects": [...]} indent=2 ensure_ascii=False, no trailing newline, via mkstemp in STATE_DIR + os.replace. Decision: stop persisting the pruned list. get_global_projects still hides entries without .tickets for display, but add_global_project keeps them on write (matches core; unmounted drives/branches without .tickets are not lost).

**2026-10-14T19:52:03Z**

PR opened: https://github.com/msampathkumar/ticket/pull/17. make test 227/227, ruff pass; webui output byte-identical to core; concurrent writers keep valid JSON. Side finding: core tk init in a dir with non-ASCII name (e.g. 'p ü') fails with 'Illegal byte sequence' at ticket line 270 (ID prefix generation) on macOS.

**2026-10-14T19:54:07Z**

Coordinator: reviewed and squash-merged PR #17. CI green. Temp file + os.replace, byte-identical to core, no on-disk pruning. Known limit: concurrent writers can drop an addition (no shared lock).
