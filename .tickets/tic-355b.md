---
id: tic-355b
status: closed
deps: [tic-2b85, tic-k65z, tic-vjkn, tic-qiet, tic-da9d, tic-8qt5]
links: []
created: 2026-10-14T19:13:15Z
type: task
priority: 2
assignee: scion-agent
parent: tic-xv7i
tags: [docs, webui]
---
# Docs: update Web UI pages for hardening changes

Update docs/plugins/webui.md, docs/workflows/webui-team.md, tk_webui/WEBUI-SPEC.md: localhost-only security model and host check, vendored offline assets, directory argument behaviour, auto-refresh, wide layout. Refresh screenshots if the layout changed.

## Acceptance Criteria

- [ ] Security model section exists
- [ ] Docs match tk webui help output
- [ ] Screenshots current


## Notes

**2026-10-14T20:18:18Z**

PR opened: https://github.com/msampathkumar/ticket/pull/32. Docs-only; make test 266/266. Screenshots regenerated from /tmp demo project (no personal paths). Found: mind map at default zoom overflows right with root off-centre (needs scroll); docs/plugins/scion-taskforce.md links blob/main but default branch is master (404).

**2026-10-14T20:19:48Z**

Coordinator: reviewed and squash-merged PR #32. CI green. Security model, command reference vs tk webui help, project-open priority, daemon behaviour, lane semantics; screenshots regenerated with demo data. Follow-ups: tic-96c9 (graph centring), scion-taskforce blob/main links via tic-ujze.
