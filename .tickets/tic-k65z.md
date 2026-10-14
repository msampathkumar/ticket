---
id: tic-k65z
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
# Web UI: stored XSS via ticket content

app.js L1125-1136, L1387 put marked.parse() output into innerHTML unsanitised. Titles, tags, ids, assignee interpolated raw into innerHTML (L467, L494, L528-541, L882-919). L541 puts t.id into inline onclick. tk github imports public issue text, so the chain XSS -> create taskforce ticket -> SCION agent runs attacker instructions is realistic.

## Design

DOMPurify on all rendered markdown; escapeHtml() helper for every interpolated value; replace inline onclick with data-* + addEventListener.

## Acceptance Criteria

- [ ] Ticket with <img src=x onerror=alert(1)> in title, tag, description, note renders inert in all views
- [ ] No inline event handlers built from ticket data


## Notes

**2026-10-14T19:34:43Z**

Plan: escapeHtml() for all innerHTML interpolations, DOMPurify (vendored 3.4.17) on marked output, replace inline onclick with listeners. Scope: app.js, index.html, static/vendor/.

**2026-10-14T19:34:43Z**

PR opened: https://github.com/msampathkumar/ticket/pull/3. make test 213/213 pass, ruff clean. Headless Chrome payload test: master fires 18 alerts, branch 0; no inline handlers from ticket data; listener actions verified.

**2026-10-14T19:38:52Z**

Coordinator: reviewed and squash-merged PR #3. CI green. Verified vendored DOMPurify 3.4.17 sha256 matches jsDelivr upstream; scanned remaining template interpolations (badges, ids via properties, toasts escaped). Browser-level tests tracked in tic-iafm.
