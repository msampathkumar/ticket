---
id: tic-8hvo
status: closed
deps: [tic-rbze, tic-wntw, tic-m0ru]
links: []
created: 2026-10-14T19:13:15Z
type: task
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [docs, agents]
---
# Docs: update agent guides and agent skill

Update AGENTS.md (root), docs/AGENTS.md, docs/agents/workflow.md, docs/agents/agent-skill.md, docs/agents/llms-txt.md, agent-skill/tk/SKILL.md, docs/workflows/cli-solo.md for the claim step, new ID format and scope/non-goals.

## Acceptance Criteria

- [ ] 5-step loop uses the safe claim command everywhere
- [ ] SKILL.md installs and matches the CLI


## Notes

**2026-10-14T20:12:56Z**

Edits: 5-step loop claim step -> 'tk start <id> --claim [--assignee]' with exit 3/4 handling in AGENTS.md, docs/AGENTS.md, docs/agents/workflow.md, agent-skill.md, SKILL.md; 6-char IDs + partial-ID note; scope/non-goals links to SPEC#non-goals; no python3 core (jq optional); GitHub plugin relabelled one-way import with untrusted-input warning; scion-taskforce described as event-driven bridge (not orchestration) per SPEC 1. Tagline unchanged. tk agent-skill --install output matches SKILL.md.

**2026-10-14T20:14:53Z**

PR opened: https://github.com/msampathkumar/ticket/pull/30. make test 266/266; skill install output identical to SKILL.md.

**2026-10-14T20:16:25Z**

Coordinator: reviewed and squash-merged PR #30. CI green. Agent loop uses tk start --claim with exit-code handling; SKILL.md install verified identical.
