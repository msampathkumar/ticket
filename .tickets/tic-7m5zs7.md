---
id: tic-7m5zs7
status: closed
deps: []
links: []
created: 2026-10-14T21:48:58Z
type: feature
priority: 1
assignee: Sampath Kumar
tags: [release, agents]
---
# Release assets: downloadable tk core (single file + zip) and skill install info

User request 2026-10-14: users and agents with only the tk skill should be able to install core without cloning. Attach core assets to every GitHub release and document the download URLs in the agent skill.

## Design

Assets with stable names (no version) so releases/latest/download/<name> works: 'tk' (the ticket script, executable), 'tk-core.zip' (ticket, LICENSE, INSTALL.md), 'SHA256SUMS'. scripts/build-dist.sh [ref] + make dist (deterministic). release.yml: build and upload right after 'Create GitHub Release' (a separate workflow on release:published would NOT fire because the release is created with GITHUB_TOKEN). New release-assets.yml with workflow_dispatch(tag) to backfill an existing release (v0.5.0) via gh release upload --clobber, taking 'ticket' from the given tag.

## Acceptance Criteria

- [ ] make dist builds tk, tk-core.zip, SHA256SUMS; CI test installs from tk-core.zip in a clean dir and runs tk init/create/ready
- [ ] release.yml uploads assets on new releases; release-assets.yml can backfill a tag
- [ ] SKILL.md documents curl install from releases/latest/download/tk and the release page; embedded copy synced (make skill-sync)
- [ ] installation.md + README 'Download a release' section; CHANGELOG [Unreleased] Added


## Notes

**2026-10-14T21:49:23Z**

Plan: scripts/build-dist.sh + make dist, release.yml upload step, release-assets.yml backfill, CI job in lint.yml, SKILL/docs/README/CHANGELOG.

**2026-10-14T21:52:56Z**

PR opened: https://github.com/msampathkumar/ticket/pull/49. make test 286 passed; dist-check, shellcheck, ruff, skill-check, check-jsonschema pass. Backfill v0.5.0 via release-assets.yml after merge.

**2026-10-14T21:54:56Z**

Coordinator: reviewed and squash-merged PR #49 (CI green incl. ubuntu/macos asset jobs). Backfilled v0.5.0 via release-assets.yml (run 38643809404): tk, tk-core.zip, SHA256SUMS attached; verified curl download, checksums and tk create/ready in a clean dir.
