---
id: tic-kyej
status: closed
deps: [tic-4h0q]
links: []
created: 2026-10-14T19:44:42Z
type: chore
priority: 3
assignee: scion-agent
parent: tic-xv7i
tags: [webui, performance]
---
# Web UI: replace Tailwind Play runtime with static CSS build

Follow-up from PR #11 (tic-vjkn). The vendored Tailwind Play runtime (~400 KB) compiles CSS in the browser and logs a production warning. A prebuilt static CSS file would be smaller and faster, but needs a build step and must cover classes built dynamically in app.js (safelist).

## Acceptance Criteria

- [ ] UI pixel-identical
- [ ] No in-browser compile; no console warning
- [ ] Build steps documented in static/vendor/README.md


## Notes

**2026-10-14T20:24:37Z**

Plan/progress: Tailwind 3.4.17 standalone CLI (sha256 verified against release sha256sums.txt) builds static/css/tailwind.css from tk_webui/tailwind.config.js (content: index.html + static/js/**/*.js). Accents are CSS variables in styles.css, so no safelist needed. Link placed after styles.css to match Play's cascade order (Play appends its <style> after styles.css). scripts/build-webui-css.sh downloads+verifies the CLI. Pixel diff vs Play: 132/132 screenshots differ but by 1-2 colour levels in semi-transparent areas (Play-vs-Play noise run shows up to 10 levels in a few spots); computed styles match on the lane sample. Running full computed-style comparison across all themes/accents/states.

**2026-10-14T21:01:44Z**

PR opened: https://github.com/msampathkumar/ticket/pull/40. Computed styles identical across light/dark x 6 accents x 6 states except one autoprefixer entry in .transition (-webkit-text-decoration-color). 114/132 screenshots pixel-identical, remaining 18 are 1-level anti-alias noise (Play-vs-Play noise: 11/132). Unminified output kept (minify changed computed styles). make test: 265 passed, 1 env-specific failure (installed ~/.local/bin/tk-scion-taskforce shadows repo plugin). shellcheck and ruff clean.

**2026-10-14T21:03:02Z**

Coordinator: reviewed and squash-merged PR #40. CI green. Committed static/css/tailwind.css (45 KB) built by scripts/build-webui-css.sh (checksum-verified CLI); computed-style parity across themes/accents/views. Follow-up: tic-wxig (CI freshness check).
