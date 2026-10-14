---
id: tic-7hsr
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: bug
priority: 1
assignee: scion-agent
parent: tic-xv7i
tags: [webui, security]
---
# Web UI: prevent option injection into tk CLI args

tk_cli.py L249 passes title as bare positional; '-p' or '--help' titles are parsed as options. Same risk for ids, dep ids, notes.

## Design

Validate ids against ticket ID pattern; reject/escape leading '-' in titles and notes, or add '--' support to tk.

## Acceptance Criteria

- [ ] Creating a ticket titled '--help' via the API either creates that title or returns 400; never runs another command path


## Notes

**2026-10-14T19:30:11Z**

Plan: validate IDs (ticket/dep/link/parent) with ^\w[\w.-]*$ in tk_cli.py and reject titles starting with '-' (tk create takes title as bare positional). Option values (-d, --design, etc.) and add-note text are taken verbatim by tk, so they stay unrestricted. Errors return (False, msg) so main.py yields 400. Behave scenarios in features/webui_cli_args.feature.

**2026-10-14T19:31:33Z**

PR opened: https://github.com/msampathkumar/ticket/pull/5. make test: 217 scenarios passed; ruff passed.

**2026-10-14T19:32:55Z**

Coordinator: reviewed and squash-merged PR #5 into master. CI green. Accepted trade-off: titles starting with '-' return 400. Follow-up noted: newlines or '/' in assignee/external_ref may break sed-based YAML updates.
