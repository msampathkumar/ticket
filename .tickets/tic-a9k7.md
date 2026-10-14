---
id: tic-a9k7
status: open
deps: []
links: []
created: 2026-10-14T21:13:48Z
type: chore
priority: 3
assignee: Sampath Kumar
tags: [github]
---
# GitHub plugin: normalise and dedupe existing tags on re-sync

Found in tic-r5v9. Tickets imported before #14 can carry raw label tags such as 'autorelease: pending' and a space-stripped duplicate 'autorelease:pending' (ensure_ticket_tags gsub(/ /,"")). Re-sync only adds the sanitised 'autorelease-pending'. Consider replacing legacy variants of imported labels with the sanitised form on re-sync (keep user-added tags).

## Acceptance Criteria

- [ ] Re-sync replaces legacy label variants with the sanitised tag, without touching non-label tags
- [ ] Behave scenario with stub gh

