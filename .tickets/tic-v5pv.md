---
id: tic-v5pv
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: bug
priority: 3
assignee: scion-agent
parent: tic-xv7i
tags: [webui]
---
# Web UI: note parser splits on any bold line

tk_cli.py L150 splits notes on any line starting with **...**, so bold text inside a note breaks it into two notes.

## Design

Match the exact timestamp pattern written by tk add-note: **YYYY-MM-DDTHH:MM:SSZ**.

## Acceptance Criteria

- [ ] Note containing a bold line renders as one note


## Notes

**2026-10-14T19:53:44Z**

Plan: split notes only on lines exactly matching **YYYY-MM-DDTHH:MM:SSZ** (tk add-note format, optional trailing whitespace/CR). Add Behave scenarios to webui_cli_args.feature-style new feature: note with bold line parses as one note; two notes still split.

**2026-10-14T19:59:04Z**

PR opened: https://github.com/msampathkumar/ticket/pull/20. Rebased on master after #17. make test 240/240, ruff pass; new scenario fails on old parser.

**2026-10-14T20:02:00Z**

Coordinator: reviewed and squash-merged PR #20. CI green.
