---
id: tic-2ml2
status: closed
deps: [tic-ujze]
links: []
created: 2026-10-14T20:25:47Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [core, agents]
---
# Core: embedded fallback skill in ticket is stale vs SKILL.md

Found in tic-ujze. The _skill_content heredoc in ticket (used by tk agent-skill when the repo copy is not available, e.g. installed tk) is out of date compared with agent-skill/tk/SKILL.md (claim step, IDs, import wording). Sync it and add a test that the two stay identical.

## Acceptance Criteria

- [ ] tk agent-skill output from an installed copy equals agent-skill/tk/SKILL.md
- [ ] Behave scenario guards drift


## Notes

**2026-10-14T20:37:37Z**

Fallback heredoc regenerated from SKILL.md (post-#36 tagline). Delimiter renamed TK_SKILL_EOF. Drift guard: scripts/sync_skill.sh (+ --check) with make skill-sync/skill-check, and features/agent_skill.feature comparing 'tk agent-skill' (and --install) from a copy outside the repo byte-for-byte with SKILL.md; both scenarios fail on the stale heredoc. Based on master after #36 merge.

**2026-10-14T20:39:42Z**

PR opened: https://github.com/msampathkumar/ticket/pull/38. make test 277/277, skill-check in sync, shellcheck clean.

**2026-10-14T20:42:57Z**

Follow-up PR: https://github.com/msampathkumar/ticket/pull/39 (CONTRIBUTING: run make skill-sync after editing SKILL.md).

**2026-10-14T20:44:19Z**

Coordinator: reviewed and squash-merged PR #38 and #39. CI green. Embedded skill synced; scripts/sync_skill.sh + make skill-sync/skill-check; drift scenario; CONTRIBUTING note. Merged master verified: 282 scenarios, skill-check and shellcheck clean.
