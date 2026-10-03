---
id: tic-jpp3
status: closed
deps: []
links: []
created: 2026-10-03T16:51:29Z
type: feature
priority: 1
assignee: scion-agent
tags: [scion-taskforce, architecture, hub]
---
# feat(scion-taskforce): implement Model 3 pluggable dual-mode SCION Hub integration

Implement Model 3 (Pluggable Dual-Mode) architecture for tk-scion-taskforce to bridge local tk task execution with centralized SCION Hub (:8080). Auto-detect running SCION Hub server, link local projects, route agent lifecycle through the Hub API for centralized environment/secrets and web UI observability, while preserving full offline fallback when Hub is stopped.

## Design

1. Hub Auto-Detection & Project Linking: Add a Hub health probe in provider preflight. Auto-link local project (scion hub link --yes) when Hub is active. 2. Dual-Mode Dispatch: Route worker dispatch via Hub API when active to inherit centralized secrets and environment variables; fallback to --no-hub local Podman execution when Hub is down. 3. Web UI Cross-Linking: In tk-webui (:8475), embed or link to the SCION Hub streaming web terminal (http://127.0.0.1:8080/agents/<id>) for active worker tickets. 4. Conflict Prevention: Prevent 409 name collisions between local Podman and Hub broker database.

## Acceptance Criteria

1. Hub probe in provider preflight detects Hub health without blocking or erroring when offline. 2. When Hub is running, project auto-links and worker agents appear in SCION Hub Web UI (:8080). 3. Workers in Hub mode inherit Hub secrets and environment variables. 4. When Hub is stopped, taskforce falls back seamlessly to local Podman runtime (--no-hub) with zero degradation. 5. tk-webui displays direct deep-link to SCION Hub agent terminal for running taskforce tickets. 6. BDD test suite passes (make test).


## Notes

**2026-10-03T20:07:21Z**

Implemented Model 3 Pluggable Dual-Mode SCION Hub integration: auto-links projects to Hub, routes lifecycle via Hub API with --no-hub fallback, templates seeded at .scion/templates/taskforce-worker/, and verifies seamless test execution.
