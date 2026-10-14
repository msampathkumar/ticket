---
id: tic-ey8z
status: closed
deps: []
links: []
created: 2026-10-14T20:00:27Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [core]
---
# Core: create/init report success when ticket file write fails

Found in tic-dmpm. cmd_create and cmd_init write via '{ ...; } > "$file"'. A redirect failure does not abort under set -e, so tk prints an ID and exits 0 with no file written.

## Acceptance Criteria

- [ ] Write failure (e.g. read-only .tickets) makes tk create/init exit non-zero with an error and no ID printed
- [ ] Behave scenario


## Notes

**2026-10-14T20:02:58Z**

Repro (read-only .tickets or invalid name): create and init print success/ID with rc 0 and fire hooks; update --title/-d rewrite (awk temp+mv) also prints Updated with rc 0. Cause: bash errexit does not fire for a failed redirection on a { ...; } group, and _update_ticket_file treated any awk failure as 'no frontmatter'. add-note, update_yaml_field, _sed_i already exit 1. Plan: explicit write checks with 'Error: cannot write ticket file <path>', remove partial file, return 1 before ID/hook.

**2026-10-14T20:06:19Z**

PR opened: https://github.com/msampathkumar/ticket/pull/25. make test 265/265, shellcheck + ruff clean. Covers create, init, update body rewrite; add-note/update_yaml_field/_sed_i already exited 1.

**2026-10-14T20:08:21Z**

Coordinator: reviewed and squash-merged PR #25. CI green. create/init/update exit 1 with 'cannot write ticket file', no ID, no hook.
