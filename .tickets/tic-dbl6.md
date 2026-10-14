---
id: tic-dbl6
status: closed
deps: [tic-v5pv]
links: []
created: 2026-10-14T19:52:36Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-xv7i
tags: [webui, core]
---
# Web UI ignores external-ref written by core

Core writes 'external-ref:' in frontmatter (ticket L445, L759) but tk_webui/tk_cli.py reads meta.get('external_ref') and SPEC 2.2 documents external_ref. External refs (e.g. gh-issue-12 from tk github) never show in the Web UI.

## Acceptance Criteria

- [ ] Web UI reads external-ref (and external_ref for compatibility)
- [ ] Web UI updates round-trip
- [ ] SPEC naming fixed via tic-6rzc


## Notes

**2026-10-14T19:54:40Z**

Plan: parser reads external-ref (core key) with fallback to legacy external_ref, coerced to str. Behave scenarios in new features/webui_external_ref.feature + own step file (avoids conflict with tic-v5pv's webui_steps.py edits): core-created ref shows in web UI; web UI update round-trips; legacy key still read. SPEC naming left to tic-6rzc.

**2026-10-14T19:59:04Z**

PR opened: https://github.com/msampathkumar/ticket/pull/21. Rebased on master after #17. make test 241/241, ruff pass; new scenarios fail on old parser. SPEC naming left to tic-6rzc.

**2026-10-14T20:02:08Z**

Coordinator: reviewed and squash-merged PR #21. CI green. Reads external-ref, falls back to external_ref. SPEC naming via tic-6rzc.
