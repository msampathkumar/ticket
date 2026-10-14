---
id: tic-jgsh
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-xv7i
tags: [webui, daemon]
---
# Web UI daemon: reliable start detection and log fd handling

server.py L67-81 checks PID after fixed 0.5s sleep; port conflicts that fail later report success. Log file handle never closed.

## Acceptance Criteria

- [ ] start polls the port until listening or timeout; reports failure on port conflict
- [ ] log fd closed in parent


## Notes

**2026-10-14T19:32:33Z**

Plan: refuse start if port already accepts connections; open log in a with-block so parent closes fd after Popen; poll proc.poll() + socket connect every 0.1s up to 10s; on early exit/timeout print failure + log path, terminate on timeout. PID identity untouched (tic-niy5).

**2026-10-14T19:34:40Z**

PR opened: https://github.com/msampathkumar/ticket/pull/7. make test 213/213, ruff pass; manual: normal start rc0, occupied port rc1, bad host early-exit rc1, parent log fd closed.

**2026-10-14T19:39:17Z**

Coordinator: reviewed and squash-merged PR #7. CI green. Start pre-checks port, polls up to 10s, reports early exit/timeout with log path; parent closes log fd.
