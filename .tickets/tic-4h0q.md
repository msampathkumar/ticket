---
id: tic-4h0q
status: closed
deps: [tic-k65z, tic-da9d, tic-8qt5, tic-vjkn]
links: []
created: 2026-10-14T19:11:34Z
type: chore
priority: 3
assignee: scion-agent
parent: tic-xv7i
tags: [webui, refactor]
---
# Web UI: split app.js into view modules

app.js is 2275 lines with 52 innerHTML uses. Split into kanban, table, graph, detail, api modules to ease review and the XSS fix.

## Acceptance Criteria

- [ ] No behaviour change; app.js split into ES modules
- [ ] make test passes


## Notes

**2026-10-14T20:01:55Z**

Plan: mechanical split of app.js into 14 ES modules under static/js/ (state, utils, theme, directory, autorefresh, api, views, kanban, table, graph, timeline, detail, create, main) via a script that only adds 'export' and computed import lines; code bodies unchanged (concatenation check). index.html loads js/main.js as type=module; main.js exposes openNewTicketModal and toggleSection on window for the inline onclick handlers. ESLint no-undef clean. Table title cap relaxed to 2xl:max-w-xl. Verifying base vs new with a Playwright e2e on fixture projects.

**2026-10-14T20:07:29Z**

PR opened: https://github.com/msampathkumar/ticket/pull/26. E2E base vs new identical (views, detail drawer, inline handlers, create, drag/drop, auto-refresh, theme), no console errors. Wheel ships static/js/*. make test 238 passed; ruff passed. Split script: scratch/split_appjs.py in the worker's brain dir.

**2026-10-14T20:09:16Z**

Coordinator: reviewed and squash-merged PR #26. CI green. Scripted verbatim split into 14 modules under static/js/, E2E parity with master verified by worker; table title 2xl:max-w-xl.
