---
id: tic-6rzc
status: closed
deps: [tic-q9lz, tic-rbze, tic-wntw, tic-m0ru, tic-5bdh]
links: []
created: 2026-10-14T19:13:15Z
type: task
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [docs, spec]
---
# Docs: update core CLI pages and SPEC

Update docs/index.md, getting-started/installation.md, getting-started/quick-start.md, core-cli/commands.md, core-cli/configuration.md, core-cli/dependencies.md, docs/SPEC.md (2.1 ID format, 2.3 note format is '**ts**' not '### Note (ts)', 4 claim command and exit codes, 5 plugin optionality), docs/PLUGIN_SPEC.md, docs/PLUGINS.md.

## Acceptance Criteria

- [ ] Every command and flag in tk help appears in commands.md and SPEC 4
- [ ] Installation page lists actual runtime requirements
- [ ] SPEC 2.3 matches tk add-note output


## Notes

**2026-10-14T20:13:36Z**

Plan: rewrite commands.md complete vs tk help; fix configuration.md (EDITOR->nano fallback, no NO_COLOR, discovery, pager, TK_ID_HASH_LENGTH/TK_LOCK_*); SPEC 2.2 external-ref, 2.3 real body format, 2.4 field values/repo files, 4 full table + write-failure; installation runtime reqs; quick-start claim + 6-char IDs; index/PLUGINS/PLUGIN_SPEC accuracy. Avoid lines changed by tic-5bdh (PR #29).

**2026-10-14T20:19:20Z**

PR opened: https://github.com/msampathkumar/ticket/pull/33. tk help coverage of commands.md and SPEC 4 checked by script (0 missing). Corrected configuration.md errors (EDITOR->nano, no NO_COLOR, discovery). make test 266/266. SPEC section 5 and the PLUGINS/PLUGIN_SPEC lines from #29 untouched.

**2026-10-14T20:20:41Z**

Coordinator: reviewed and squash-merged PR #33. CI green. commands.md/SPEC 4 complete vs tk help; configuration corrected (nano, no NO_COLOR); SPEC 2.2-2.5 field values and repo files; installation/quick-start/index updated.
