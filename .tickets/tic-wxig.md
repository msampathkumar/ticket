---
id: tic-wxig
status: closed
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


## Notes

**2026-10-14T21:30:59Z**

PR https://github.com/msampathkumar/ticket/pull/47: lint.yml webui-css job (make webui-css-check), Makefile webui-css/webui-css-check, CONTRIBUTING line, regenerated tailwind.css (master copy was stale: +.inline/.grow/.resize, harmless). Linux x64 and macOS arm64 builds byte-identical (blob 7b9bf0b). make test 285 passed, ruff clean, all 5 CI checks green.

**2026-10-14T21:31:26Z**

Coordinator: reviewed and squash-merged PR #47. CI green incl. new 'Web UI CSS is fresh' job. make webui-css / webui-css-check; Linux and macOS builds byte-identical; CSS regenerated (+.inline/.grow/.resize, harmless).
