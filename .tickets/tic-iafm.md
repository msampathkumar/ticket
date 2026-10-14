---
id: tic-iafm
status: closed
deps: [tic-2b85, tic-k65z, tic-7hsr]
links: []
created: 2026-10-14T19:11:34Z
type: chore
priority: 3
assignee: scion-agent
parent: tic-xv7i
tags: [webui, docs, tests]
---
# Web UI: fix doc/version drift and add basic tests

SPEC 2.3 documents notes as '### Note (ts)' but CLI writes '**ts**'. FastAPI app version 0.1.0 vs CLI 0.4.0. prog_name ternary in main.py L283 has identical branches. No Web UI scenarios in features/.

## Acceptance Criteria

- [ ] Single version source (FastAPI app, CLI, WEBUI-SPEC)
- [ ] prog_name ternary cleaned up
- [ ] A few black-box API scenarios: create, list, foreign Host rejected, XSS payload stored inert, '--help' title handled


## Notes

**2026-10-14T19:13:15Z**

SPEC 2.3 note-format fix moved to the core docs ticket.

**2026-10-14T20:01:06Z**

Plan: tk_webui.__version__ as single source (app, --version, --help); scenario enforces match with pyproject (static, release.yml reads it) and WEBUI-SPEC; drop prog_name ternary; API scenarios via TestClient. httpx added to dev group (SecureCoder scanner not running, scan skipped per skill).

**2026-10-14T20:01:06Z**

PR opened: https://github.com/msampathkumar/ticket/pull/23. make test 249/249 (11 new), ruff clean, clean Python 3.11 --locked run passes. Note: existing CLI scenarios leak ticket_test_* entries into the real ~/.local/state/tk/projects.json via the core script (pre-existing; new scenarios isolate HOME).

**2026-10-14T20:02:58Z**

Coordinator: reviewed and squash-merged PR #23. CI green. __version__ single source + drift check, 11 TestClient API scenarios, httpx dev dep. Follow-up: tic-0ok7 (HOME isolation for all scenarios; also drop duplicate add_cleanup).
