---
id: tic-xliq
status: closed
deps: []
links: []
created: 2026-10-14T21:03:17Z
type: bug
priority: 3
assignee: Sampath Kumar
tags: [release, packaging]
---
# AUR PKGBUILDs point at upstream wedow/ticket

Found in tic-fa2r. pkg/aur/*/PKGBUILD url/source/Maintainer reference github.com/wedow/ticket. If AUR publishing is enabled (AUR_SSH_KEY secret; currently not set), ticket-core would download wedow's tag, not this fork's. Decide: point to msampathkumar/ticket with own maintainer line, or remove AUR packaging from this fork.

## Acceptance Criteria

- [ ] PKGBUILD url/source/maintainer match the publishing repo, or AUR packaging removed
- [ ] release.yml AUR step consistent with the decision


## Notes

**2026-10-14T21:25:49Z**

Plan: remove AUR packaging per user decision (pkg/aur, scripts/publish-aur.sh, release.yml AUR step, doc refs, CHANGELOG Removed).

**2026-10-14T21:27:49Z**

PR opened: https://github.com/msampathkumar/ticket/pull/45. Removed pkg/aur, scripts/publish-aur.sh, release.yml AUR step (sha step kept for Homebrew; pkg/extras.txt kept). make test 285 passed, shellcheck/ruff clean, check-jsonschema ok.

**2026-10-14T21:29:22Z**

Coordinator: reviewed and squash-merged PR #45. CI green. Removed pkg/aur, publish-aur.sh, release.yml AUR step (user decision). Homebrew step kept (own tap msampathkumar/homebrew-tools).
