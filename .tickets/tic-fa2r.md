---
id: tic-fa2r
status: closed
deps: [tic-kyej, tic-r5v9]
links: []
created: 2026-10-14T20:59:00Z
type: chore
priority: 1
assignee: Sampath Kumar
tags: [release]
---
# Release 0.5.0: bump version across the repo

User-approved 2026-10-14: bump 0.4.0 -> 0.5.0 after tic-kyej merges. Merging to master triggers release.yml (tag v0.5.0 + GitHub release with the CHANGELOG [0.5.0] section).

## Acceptance Criteria

- [ ] All version strings 0.5.0 (pyproject, package.json, tk_webui/__init__, ticket help/version, plugin headers/VERSION, plugin specs, docs examples, AUR PKGBUILDs, uv.lock)
- [ ] CHANGELOG: [Unreleased] renamed to [0.5.0] - <date>, new empty [Unreleased] above
- [ ] Version drift scenario passes; make test, shellcheck, ruff clean
- [ ] Merged only after tic-kyej


## Notes

**2026-10-14T21:00:38Z**

Bumped 0.4.0 -> 0.5.0 in pyproject, uv.lock (tk-webui entry; uv lock --check OK), package.json, tk_webui/__init__.py, ticket help/version, github plugin header+VERSION, webui plugin header, GITHUB-SPEC, WEBUI-SPEC, docs/PLUGINS.md, 3 AUR PKGBUILDs. scion-taskforce stays 0.1.0 (independent scheme). CHANGELOG: [0.5.0] - 2026-10-14 + empty [Unreleased]; added #37/#38 lines; release.yml awk dry-run extracts exactly the 0.5.0 section. AUR: sha256sums=('SKIP') and publish-aur.sh rewrites pkgver/sha256 at release; but url/source point at wedow/ticket (upstream), flagged.

**2026-10-14T21:02:41Z**

PR opened: https://github.com/msampathkumar/ticket/pull/41 (merge only after tic-kyej). make test 282/282, shellcheck/ruff/skill-check clean. No tags or releases created.

**2026-10-14T21:06:25Z**

Rebased onto master after #40 (tic-kyej); added #40 line to CHANGELOG [0.5.0]; llms-full regenerated. make test 282/282, shellcheck/ruff/skill-check clean. Force-pushed (with lease) to PR #41.

**2026-10-14T21:17:59Z**

Rebased onto master after #42/#43; CHANGELOG [0.5.0] lines for #42 (Changed/Docs) and #43 (Fixed); llms-full regenerated. make test 285/285, shellcheck/ruff/skill-check clean. Force-pushed with lease.

**2026-10-14T21:19:24Z**

Coordinator: reviewed and squash-merged PR #41. CI green. Version 0.5.0 everywhere; CHANGELOG [0.5.0] - 2026-10-14. release.yml triggered.
