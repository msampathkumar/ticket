---
id: tic-wntw
status: closed
deps: []
links: []
created: 2026-10-14T19:07:32Z
type: feature
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [core, concurrency]
---
# Reduce ticket ID collision risk across branches

IDs use a 4-char random hash. Parallel agents on separate branches can collide on merge.

## Design

Options: longer hash (6+), or timestamp-derived component. Keep short-ID prefix resolution working for existing tickets.

## Acceptance Criteria

- [ ] New IDs have materially lower collision probability
- [ ] Existing 4-char IDs still resolve
- [ ] SPEC 2.1 updated


## Notes

**2026-10-14T19:42:47Z**

Plan: lengthen random hash 4 -> 6 lowercase alnum chars (TK_ID_HASH_LENGTH 4-32 override), /dev/urandom with $RANDOM fallback, retry up to 10x on local file collision. Lowercase kept (larger mixed-case alphabet would collide on case-insensitive FS). Legacy 4-char IDs resolve via existing exact-then-partial lookup. SPEC 2.1 updated.

**2026-10-14T19:44:48Z**

PR opened: https://github.com/msampathkumar/ticket/pull/12. make test 231/231 pass, ruff clean. update_yaml_field untouched (reserved for tic-xypv).

**2026-10-14T19:47:10Z**

CI ShellCheck SC2034 (unused retry var) fixed: loop now uses _; shellcheck -S warning ticket clean locally; pushed to PR #12.

**2026-10-14T19:48:55Z**

Coordinator: reviewed and squash-merged PR #12 (after ShellCheck SC2034 fix). CI green. Default hash 6 chars (TK_ID_HASH_LENGTH 4-32), local collision retry, old 4-char IDs still resolve; SPEC 2.1 updated.
