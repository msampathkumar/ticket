---
id: tic-a9k7
status: closed
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


## Notes

**2026-10-14T21:25:42Z**

Plan: in ensure_ticket_tags, drop legacy variants (raw label, space-stripped) of current labels, add sanitised tag, dedupe; keep other tags. Add Behave scenario.

**2026-10-14T21:28:20Z**

PR opened: https://github.com/msampathkumar/ticket/pull/46. make test 286/286 pass, ruff clean, shellcheck clean.

**2026-10-14T21:29:44Z**

Coordinator: reviewed and squash-merged PR #46. CI green. Re-sync replaces space-stripped legacy label variants with sanitised tags, dedupes, keeps user tags.
