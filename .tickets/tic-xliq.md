---
id: tic-xliq
status: open
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

