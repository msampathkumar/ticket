---
id: tic-ujze
status: closed
deps: [tic-h90e, tic-6rzc, tic-8hvo, tic-355b, tic-x3nz, tic-iafm]
links: []
created: 2026-10-14T19:13:15Z
type: task
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [docs, release]
---
# Docs: consistency pass, CHANGELOG and llms rebuild

Final pass after all docs tickets: cross-check README, docs site, CLI help strings and specs; add CHANGELOG entries; run make docs-build to regenerate llms.txt and llms-full.txt; verify site builds without warnings.

## Acceptance Criteria

- [ ] make docs-build succeeds; llms files regenerated
- [ ] CHANGELOG lists security fixes and behaviour changes
- [ ] make test passes


## Notes

**2026-10-14T20:18:47Z**

Coordinator: include fix for docs/plugins/scion-taskforce.md links pointing to blob/main (default branch is master), found in tic-355b.

**2026-10-14T20:25:08Z**

Consistency pass done: POSIX Bash/bi-directional/orchestrator/PR-review/offline-tagline claims fixed across CONTRIBUTING, plugins/README (emoji headings removed), llms.txt, index, PLUGINS, install.sh help, plugin tk-plugin descriptions, scion cli help, webui description, SPEC/AGENTS wording, zensical nav; blob/main -> blob/master; GitHub external-ref key. CHANGELOG [Unreleased]: Security/Added/Changed/Fixed for #3-#33. make docs-build: 'No issues found'. Finding (not fixed, core scope): ticket's embedded fallback skill (_skill_content heredoc, used by installed copies of tk) is stale vs agent-skill/tk/SKILL.md.

**2026-10-14T20:35:40Z**

PR opened: https://github.com/msampathkumar/ticket/pull/36. New tagline applied everywhere (fallback skill left for tic-2ml2). CHANGELOG Security/Added/Changed/Fixed for #3-#35. make docs-build: No issues found; make test 275/275; shellcheck + ruff clean. Branch re-created on current master via cherry-pick (unpushed) to include #34/#35.

**2026-10-14T20:37:07Z**

Coordinator: reviewed and squash-merged PR #36. CI green. New tagline everywhere, stale claims removed, blob/master links, CHANGELOG [Unreleased] for #3-#35, llms rebuilt, docs build clean. Follow-up: tic-2ml2.
