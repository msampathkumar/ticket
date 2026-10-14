---
id: tic-2b85
status: closed
deps: []
links: []
created: 2026-10-14T19:11:33Z
type: bug
priority: 0
assignee: scion-agent
parent: tic-xv7i
tags: [webui, security]
---
# Web UI: remove permissive CORS and add host check

tk_webui/main.py L42-48 sets allow_origins=['*'] with credentials. Any website can call localhost:8475 to list directories (/api/browse), read any .tickets dir (/api/tickets), and create dirs/tickets anywhere (/api/init mkdir parents=True). No Host check, so DNS rebinding also works.

## Design

Drop CORSMiddleware (UI is same-origin). Add TrustedHostMiddleware for 127.0.0.1/localhost. Consider restricting directory params to registered projects.

## Acceptance Criteria

- [ ] Cross-origin requests from another origin are rejected
- [ ] Requests with foreign Host header get 400
- [ ] UI still works on 127.0.0.1:8475 and localhost:8475


## Notes

**2026-10-14T19:25:11Z**

Plan: drop CORSMiddleware; add TrustedHostMiddleware (127.0.0.1, localhost, ::1 + configured --host via TK_WEBUI_HOST env); reject non-GET requests whose Origin host:port does not match Host. Verify with curl on port 18475.

**2026-10-14T19:31:05Z**

PR opened: https://github.com/msampathkumar/ticket/pull/4. make test 213/213 pass, ruff pass, manual curl verified (foreign Host 400, foreign Origin POST 403, localhost/127.0.0.1 200). No Behave scenarios: no FastAPI in test env (see tic-iafm).

**2026-10-14T19:32:28Z**

Coordinator: reviewed and squash-merged PR #4 into master. CI green (BDD 3.11/3.13, ruff, shellcheck). Follow-ups: IPv6 [::1] host not allowlisted; Web UI API tests tracked in tic-iafm.
