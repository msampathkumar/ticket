---
id: tic-x3nz
status: closed
deps: []
links: []
created: 2026-10-14T19:07:32Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [github, docs]
---
# Fix GitHub plugin 'bi-directional' claim

tk-github only runs gh issue list / gh pr list (import). Docs and README call it bi-directional sync.

## Acceptance Criteria

- [ ] Docs say 'import' until write-back exists, or write-back is implemented and tested
- [ ] README, docs/plugins/github.md, GITHUB-SPEC.md consistent


## Notes

**2026-10-14T19:13:15Z**

Also add a warning that imported issue/PR text is untrusted input (see tic-k65z). Covers docs/plugins/github.md, plugins/github/GITHUB-SPEC.md, plugins/README.md, docs/PLUGINS.md.

**2026-10-14T19:40:07Z**

Confirmed tk-github is import-only: it calls gh issue list / gh pr list / gh auth status and only writes local tickets (creates open items, closes local tickets for closed/merged items). Plan: reword to 'import (one-way)' in GITHUB-SPEC.md, docs/plugins/github.md, plugins/README.md, docs/PLUGINS.md, README GitHub bullet and plugin help/describe strings; add untrusted-input warning; fix 'read/write access' prerequisite to read access. Command names (sync/unsync) and the github-sync tag stay unchanged.

**2026-10-14T19:42:11Z**

PR opened: https://github.com/msampathkumar/ticket/pull/9. make test: 213 scenarios passed; bash -n OK. Found while reading: tk-github passes the GitHub issue/PR title to 'tk super create' as a bare positional, so a title starting with '-' is misparsed (same class as tic-7hsr). Not fixed here because this ticket is docs-only.

**2026-10-14T19:43:54Z**

Coordinator: reviewed and squash-merged PR #9. CI green. Plugin wording now one-way import with untrusted-input warning. Follow-up security bug: tic-ka18.
