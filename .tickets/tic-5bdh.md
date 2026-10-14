---
id: tic-5bdh
status: closed
deps: [tic-m0ru]
links: []
created: 2026-10-14T19:07:32Z
type: chore
priority: 3
assignee: scion-agent
parent: tic-4294
tags: [docs, spec]
---
# Resolve SPEC contradiction: tk-webui listed as non-optional plugin

SPEC.md section 5: 'Except for tk-webui, all plugins are optional.' Conflicts with the zero-dependency core principle.

## Acceptance Criteria

- [ ] SPEC states all plugins are optional (or justifies the exception)


## Notes

**2026-10-14T20:13:36Z**

PR opened: https://github.com/msampathkumar/ticket/pull/29. SPEC 5 now says all plugins optional (Web UI only in --full bundle); aligned CONTRIBUTING, PLUGIN_SPEC 2.1, PLUGINS.md, install.sh --help. make test 266/266, shellcheck clean.

**2026-10-14T20:15:01Z**

Coordinator: reviewed and squash-merged PR #29. CI green. SPEC 5, PLUGIN_SPEC, PLUGINS.md, CONTRIBUTING, install.sh help aligned.
