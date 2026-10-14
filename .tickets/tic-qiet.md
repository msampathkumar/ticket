---
id: tic-qiet
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: bug
priority: 1
assignee: scion-agent
parent: tic-xv7i
tags: [webui]
---
# Web UI: 'tk webui <dir>' ignores the directory argument

main.py L288/L358 set INITIAL_PROJECT_DIR but nothing reads it. Frontend (app.js L161) falls back to localStorage or '.', which resolves to the server cwd. Affects 'tk webui server start <dir>' too.

## Design

Add GET /api/config returning initial_dir; frontend prefers ?dir= param, then config, then localStorage.

## Acceptance Criteria

- [ ] 'tk webui /path' opens /path even when localStorage holds another project


## Notes

**2026-10-14T19:42:36Z**

Plan: GET /api/config {initial_dir} from INITIAL_PROJECT_DIR, set only when a dir is given (daemon always passes one). app.js priority: ?dir=, initial_dir, localStorage, '.'.

**2026-10-14T19:42:36Z**

PR opened: https://github.com/msampathkumar/ticket/pull/10. make test 219/219, ruff clean. Headless Chrome: explicit dir, ?dir= override, no-dir localStorage fallback, daemon start <dir> all pass.

**2026-10-14T19:43:17Z**

Coordinator review PR #10: requested change - plain 'tk webui' must open cwd (matches help text and daemon behaviour); keep /api/config and ?dir= priority.

**2026-10-14T19:45:46Z**

Review fix pushed to PR #10: plain 'tk webui' and options-only launches open cwd again (main.py launch paths restored to master); /api/config and frontend priority kept. make test 219/219, ruff clean; headless checks pass for explicit dir, ?dir= override, options-only from cwd, daemon, uvicorn-direct fallback to localStorage.

**2026-10-14T19:47:26Z**

Coordinator: reviewed (one revision) and squash-merged PR #10. CI green. CLI launches always pass initial dir (given or cwd) via GET /api/config; frontend priority ?dir= > initial_dir > localStorage > '.'.
