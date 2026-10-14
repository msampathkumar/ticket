---
id: tic-niy5
status: closed
deps: [tic-jgsh]
links: []
created: 2026-10-14T19:11:34Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-xv7i
tags: [webui, daemon]
---
# Web UI daemon: verify PID identity before stop

server.py L108-118 sends SIGTERM/SIGKILL to whatever PID is in webui.json; PID reuse can kill an unrelated process.

## Acceptance Criteria

- [ ] stop checks the process command line contains tk_webui before signalling


## Notes

**2026-10-14T19:45:08Z**

Plan: add _is_webui_process(pid, port) reading /proc/<pid>/cmdline or 'ps -p <pid> -o command='; require 'tk_webui' and '--port <port>' in it. get_server_info (used by status/start/stop) treats mismatches as stale and removes the PID file; stop re-checks identity before SIGKILL.

**2026-10-14T19:47:31Z**

PR opened: https://github.com/msampathkumar/ticket/pull/13. make test 227/227, ruff pass; manual: real server stop ok, reused PID (sleep) not signalled + stale file removed, port mismatch treated as stale. Fixed a substring bug in port match during testing.

**2026-10-14T19:49:10Z**

Coordinator: reviewed and squash-merged PR #13. CI green (incl. Linux /proc path via CI env not directly exercised). Command line must contain tk_webui and matching --port token.
