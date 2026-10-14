---
id: tic-wxig
status: open
deps: []
links: []
created: 2026-10-14T21:02:09Z
type: chore
priority: 3
assignee: Sampath Kumar
parent: tic-xv7i
tags: [webui, ci]
---
# Web UI: CI check that prebuilt tailwind.css is fresh

Follow-up from PR #40 (tic-kyej). New Tailwind classes need scripts/build-webui-css.sh; a forgotten rebuild silently drops styles. Add a CI job (or make target) that rebuilds and fails on diff, plus a CONTRIBUTING line.

## Acceptance Criteria

- [ ] CI fails when static/css/tailwind.css is stale
- [ ] CONTRIBUTING documents the rebuild step

