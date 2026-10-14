---
id: tic-r5v9
status: closed
deps: []
links: []
created: 2026-10-14T21:07:53Z
type: bug
priority: 1
assignee: Sampath Kumar
parent: tic-xv7i
tags: [webui]
---
# Web UI: one malformed ticket breaks the whole board (500 on /api/tickets)

User report 2026-10-14: opening ~/github/a2a-cli shows 'Failed to load tickets'. /api/tickets returns 500: pydantic ValidationError on ac-93c2.md, tags: [..., autorelease: pending] - YAML parses 'autorelease: pending' inside a flow list as a mapping {autorelease: pending}, not a string. The tag came from a GitHub label imported before #14 sanitised labels. tk_cli.parse_ticket_markdown passes list items to the Ticket model as-is, and get_all_tickets lets one bad file fail the whole request.

## Acceptance Criteria

- [ ] Non-string list items in tags/deps/links are coerced to strings (mapping {k: v} -> 'k: v')
- [ ] A ticket that still fails to parse/validate is skipped (logged), the rest of the board loads
- [ ] Behave scenario with the a2a-cli style tags line
- [ ] Opening ~/github/a2a-cli works


## Notes

**2026-10-14T21:09:14Z**

Plan: _as_str_list() coerces tags/deps/links items (mapping {k: v} -> 'k: v', None dropped, others str()); also str() id/assignee/parent. get_all_tickets wraps each parse in try/except, logs a warning and skips. Behave scenarios via tk_cli and TestClient API. Verify read-only on a copy of a2a-cli/.tickets in /tmp/r5v9.

**2026-10-14T21:13:07Z**

PR opened: https://github.com/msampathkumar/ticket/pull/43. make test 285/285, ruff pass; scenarios error on old code. a2a-cli copy: old ValidationError, new 16/16 tickets + API 200. Core show/ls/query handle the line (query JSONL valid). Core quirk: tag filter strips spaces, so ls -T 'autorelease: pending' matches nothing while -T autorelease:pending matches. Origin: pre-tic-ka18 GitHub import wrote the raw label; ensure_ticket_tags strips spaces on merge, producing the 'autorelease:pending' duplicate.

**2026-10-14T21:14:22Z**

Coordinator: reviewed and squash-merged PR #43. CI green. List fields coerced item by item (mapping -> 'k: v'); unparseable tickets logged and skipped. Verified on a read-only copy of a2a-cli (16 tickets load). Follow-up: tic-a9k7.
