---
id: tic-q9lz
status: closed
deps: []
links: []
created: 2026-10-14T19:07:32Z
type: bug
priority: 1
assignee: scion-agent
parent: tic-4294
tags: [core, docs]
---
# Remove python3/jq from core or relabel dependency claim

ticket uses python3 in register_global_project (L165) and _update_ticket_file (L436, used by tk update); tk query filters need jq. README/SPEC/AGENTS claim a zero-dependency POSIX core. The script is Bash, not POSIX sh.

## Design

Preferred: rewrite both python3 blocks in awk/sed. Fallback: document python3 as optional and degrade gracefully. Reword 'POSIX Bash' to 'portable Bash'.

## Acceptance Criteria

- [ ] tk create/update/init work with python3 absent from PATH (or docs state the requirement)
- [ ] README, SPEC.md, AGENTS.md, llms files consistent
- [ ] make test passes


## Notes

**2026-10-14T19:28:55Z**

Plan: replace both python3 blocks in core ticket with awk/Bash (register_global_project: awk JSON reader for {projects:[...]} and legacy list, atomic temp+mv write; _update_ticket_file: awk with ENVIRON inputs). jq stays optional for tk query filters only. Differential-tested against old python version (identical output across 24 update cases). New features/ticket_no_python.feature shadows python3 with a failing stub.

**2026-10-14T19:33:48Z**

PR opened: https://github.com/msampathkumar/ticket/pull/6. make test 215/215 pass, ruff clean. python3 removed from core; jq optional only for tk query filters. Docs wording (POSIX Bash / zero-dependency claims) left to tic-h90e/tic-6rzc.

**2026-10-14T19:35:12Z**

Coordinator: reviewed and squash-merged PR #6. CI green. Core no longer calls python3; jq optional for tk query filters only. projects.json written atomically on core side (tk_cli.py side tracked in tic-aoq8). Docs wording tracked in tic-h90e / tic-6rzc.
