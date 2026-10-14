---
id: tic-m0ru
status: closed
deps: []
links: []
created: 2026-10-14T19:07:32Z
type: task
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [docs, spec]
---
# Define core scope and non-goals in SPEC section 1

Recent work centres on scion-taskforce; USER.md vision is a multi-agent orchestrator while the tagline says minimal. State explicitly: tk core is the minimal task queue; orchestration lives in plugins. List what core will never do. Consider a sharper tagline, e.g. 'A Git-native task queue that many coding agents can safely share.'

## Acceptance Criteria

- [ ] SPEC section 1 has a Non-goals list
- [ ] Tagline agreed and consistent across README, SPEC, AGENTS.md, llms files


## Notes

**2026-10-14T20:08:29Z**

PR opened: https://github.com/msampathkumar/ticket/pull/27. SPEC section 1: Scope, Non-goals, Bash 3.2+ portability wording (smoke-tested on /bin/bash 3.2.57). Tagline unchanged; 3 options offered in PR for the user. Remaining AC (tagline consistent across README/AGENTS/llms) depends on the user's tagline choice and the docs tickets.

**2026-10-14T20:11:00Z**

Coordinator: reviewed and squash-merged PR #27. CI green. SPEC section 1 Scope + Non-goals; portability wording corrected. Tagline unchanged pending user choice; propagation handled by tic-h90e/tic-6rzc/tic-8hvo/tic-ujze.
