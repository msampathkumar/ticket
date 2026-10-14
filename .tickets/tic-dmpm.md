---
id: tic-dmpm
status: closed
deps: []
links: []
created: 2026-10-14T19:52:37Z
type: bug
priority: 3
assignee: scion-agent
parent: tic-4294
tags: [core]
---
# Core: 'Illegal byte sequence' on tk init in non-ASCII directory (macOS)

Reported in tic-aoq8 testing: on macOS, tk init in a directory named with non-ASCII chars (e.g. 'p ü"3') prints 'Illegal byte sequence' around ticket L270, likely in ID prefix generation (tr/sed under a UTF-8 locale on BSD tools). Project is still registered.

## Acceptance Criteria

- [ ] tk init in a non-ASCII-named dir prints no error and yields a valid ASCII prefix
- [ ] Behave scenario


## Notes

**2026-10-14T19:57:14Z**

Root cause: generate_id prefix uses awk substr on the folder name; BSD awk is byte-wise, so a non-ASCII first char is cut mid-UTF-8 sequence, giving an invalid filename. The redirect fails with 'Illegal byte sequence' and NO ticket file is written (tk create even prints the ID with rc 0). Fix: strip the folder name to ASCII [A-Za-z0-9 _-] under LC_ALL=C before deriving the prefix; fallback 'tk' if empty.

**2026-10-14T20:00:01Z**

PR opened: https://github.com/msampathkumar/ticket/pull/22. make test 241/241, shellcheck + ruff clean. Old script wrote no ticket file at all in non-ASCII dirs (create printed ID, rc 0).

**2026-10-14T20:02:14Z**

Coordinator: reviewed and squash-merged PR #22. CI green. Prefix filtered with LC_ALL=C tr; previously no ticket file was written. Follow-up: tic-ey8z.
