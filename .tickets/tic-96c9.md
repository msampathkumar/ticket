---
id: tic-96c9
status: closed
deps: []
links: []
created: 2026-10-14T20:18:47Z
type: bug
priority: 3
assignee: scion-agent
parent: tic-xv7i
tags: [webui]
---
# Web UI: Tree Graph opens off-centre at default zoom

Found in tic-355b. At default zoom the Tree Graph root sits right of centre and the tree overflows to the right; the canvas opens scrolled left, so users must scroll to find it.

## Acceptance Criteria

- [ ] On open (and on Reset View) the tree is centred / fits the viewport at 1280 and 2560
- [ ] Both orientations


## Notes

**2026-10-14T20:21:57Z**

Cause: canvas has a fixed 1200px minimum and is left-aligned in the scroll wrapper, the wrapper opens at scrollLeft 0, and transform: scale() leaves the scroll extent unchanged. Plan (graph.js, plus a one-line Reset handler change in main.js where the hook lives): size the canvas to its content; scale with CSS zoom (transform fallback) so scroll extents follow zoom; centre a narrow canvas with a margin offset; fit-to-width (0.4-1.0) and centre on first render, orientation/project change, view switch (ResizeObserver) and Reset View; keep the visible centre when using the zoom buttons.

**2026-10-14T20:29:05Z**

PR opened: https://github.com/msampathkumar/ticket/pull/34. make test 266/266. Playwright at 1280/2560, both orientations, 3 projects: fitted trees centred (equal gaps), 61-ticket tree at min zoom 0.4 centred+scrollable; zoom buttons keep centre; Reset View and view switch refit. main.js Reset handler changed (1 line).

**2026-10-14T20:30:29Z**

Coordinator: reviewed and squash-merged PR #34. CI green. Content-sized canvas, CSS zoom with transform fallback, fit+centre on open/view switch/reset; measured at 1280/2560 both orientations.
