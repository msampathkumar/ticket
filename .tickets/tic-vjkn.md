---
id: tic-vjkn
status: closed
deps: []
links: []
created: 2026-10-14T19:11:34Z
type: chore
priority: 1
assignee: scion-agent
parent: tic-xv7i
tags: [webui, security, supply-chain]
---
# Web UI: vendor and pin frontend dependencies

index.html L10-35 loads Tailwind Play CDN, lucide@latest, unversioned marked from public CDNs without SRI. Supply-chain risk; UI breaks offline (confidential projects).

## Acceptance Criteria

- [ ] All JS/CSS served from static/ with pinned versions (or pinned + SRI)
- [ ] UI works with no network


## Notes

**2026-10-14T19:41:27Z**

Decision: vendor pinned Tailwind Play runtime 3.4.17 (same build cdn.tailwindcss.com serves today) instead of a static CSS build: pixel-identical, no Node build step, handles dynamic classes in app.js. Pinned lucide 1.57.0 and marked 15.0.12 (versions the unversioned CDN URLs currently resolve to), sortable 1.15.2. Hashes match npm tarball + jsDelivr. Headless Chrome with DNS blocked: 85 icons rendered, UI pixel-identical to online master except project path text.

**2026-10-14T19:43:15Z**

PR opened: https://github.com/msampathkumar/ticket/pull/11. make test 219/219, ruff pass, offline headless render verified; hashes listed in PR and static/vendor/README.md.

**2026-10-14T19:44:42Z**

Coordinator: reviewed and squash-merged PR #11. CI green. Independently verified sha256 of lucide 1.57.0, sortable 1.15.2, marked 15.0.12 vs jsDelivr and Tailwind Play 3.4.17 vs cdn.tailwindcss.com. Follow-up: tic-kyej static Tailwind build.
