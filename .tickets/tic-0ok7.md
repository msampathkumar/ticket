---
id: tic-0ok7
status: closed
deps: []
links: []
created: 2026-10-14T20:02:43Z
type: chore
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [tests]
---
# Tests: isolate HOME/state dir for all Behave scenarios

Found in tic-iafm. CLI scenarios run tk init/create with the developer's real HOME, so register_global_project adds every ticket_test_* temp dir to ~/.local/state/tk/projects.json (~200 entries now; ticket_creation.feature adds 16 per run). Isolate HOME (and tk_cli.STATE_DIR) per scenario in features/environment.py; drop the ad-hoc per-step isolation (webui_api_steps registers restore() twice).

## Acceptance Criteria

- [ ] make test leaves ~/.local/state/tk/projects.json byte-identical
- [ ] No per-feature HOME hacks remain
- [ ] make test passes


## Notes

**2026-10-14T20:08:46Z**

Plan: per-scenario HOME=<test_dir>/home + tk_cli.STATE_DIR/PROJECTS_FILE in environment.py, restored after; remove ad-hoc HOME in steps/features. Real projects.json not cleaned (user data).

**2026-10-14T20:08:46Z**

PR opened: https://github.com/msampathkumar/ticket/pull/28. make test 261/261. Stand-in HOME full-suite run: projects.json sha256 identical; master baseline changes it. Real-HOME run with marked TMPDIR: 0 entries from this run (other workers' old-branch suites still add entries concurrently).

**2026-10-14T20:11:01Z**

Coordinator: reviewed and squash-merged PR #28. CI green. Per-scenario HOME + tk_cli state dir in environment.py; real projects.json verified byte-identical by worker. Existing 270 polluted entries left for user decision.
