# Announcing `tk` v0.2: The Minimal Task Tracker with Dependency Intelligence

*Published: September 2026*

Modern software development with autonomous AI coding agents moves fast. But coordinating work between humans and AI assistants often breaks down: issue trackers live behind slow web interfaces, require internet access, or lack structured dependency graphs that agents can parse deterministically.

Today, we're introducing **`tk` (ticket) v0.2** — a zero-database, POSIX-fast task management system built from first principles for developers and AI pair programmers.

---

## The Philosophy: Pure Plain Text & Unix Speed

`tk` stores everything in `.tickets/*.md` files with clean YAML frontmatter, fully version-controlled in Git:

```markdown
---
id: tk-a1b2
title: "Implement OAuth2 callback handler"
status: open
type: task
priority: 2
deps:
  - tk-c3d4
created: 2026-09-27T10:00:00Z
---

### Acceptance Criteria
- [ ] Parse authorization code from query params
- [ ] Exchange token with provider
```

### Why Plain Text Matters
- **Offline First**: Works on a plane, on a train, or behind air-gapped dev environments.
- **Git Native**: Branch, merge, diff, and review tasks alongside the code they describe.
- **Zero Runtime Dependencies**: The core CLI is pure POSIX Bash using standard `awk` and `sed`. It executes in sub-milliseconds with zero Python or Node overhead.

---

## Dependency Intelligence for Autonomous Agents

AI coding agents (Antigravity, Claude, Cursor, Copilot) frequently pick up tasks out of order or collide on dependent features.

`tk` solves this with native **Directed Acyclic Graph (DAG)** tracking:

```bash
# Add dependency: tk-002 depends on tk-001
tk dep tk-002 tk-001

# List only tasks whose dependencies are 100% satisfied
tk ready
```

When an agent finishes work and runs `tk close tk-001`, `tk` unblocks downstream tickets in real time.

---

## What's New in v0.2

### 1. Interactive Web UI & Kanban Canvas
Start the browser dashboard with `tk webui`:
- **4-Lane Drag & Drop Kanban**: Backlog, Open, In Progress, Closed.
- **Interactive DAG Mind Map**: Dynamic node graph with layout toggles, multi-parent linking, and full dependency visualization.
- **High Contrast & Accessible Theme Engine**: Indigo default theme with support for emerald, violet, amber, and slate modes.
- **Table & Timeline Views**: Quick multi-attribute sorting and schedule inspection.

### 2. Multi-OS CI/CD & Automated Linting
- GitHub Actions test matrix across Ubuntu and macOS on Python 3.9 through 3.13.
- Integrated `shellcheck` and `ruff` linting pipelines.

### 3. Reusable AI Agent Skill
Install the official skill for autonomous coding assistants:
```bash
./install.sh --skill
```

---

## Getting Started

Clone the repository and install `tk`:

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket
./install.sh --all
```

Initialize your first ticket:
```bash
tk init
tk create "Build user dashboard" -t feature -p 1
tk ls
```

Check out the project on [GitHub](https://github.com/msampathkumar/ticket).
