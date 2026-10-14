---
title: ticket (tk)
description: Dependency-aware, Git-friendly task queue for humans and coding agents.
---

# <img src="images/logo.svg" width="36" height="36" alt="tk logo" style="vertical-align: -6px; display: inline-block;" /> ticket (tk)

> Dependency-aware, Git-friendly task queue for humans and coding agents.

---

## Terminal Demo

![ticket CLI Demo](images/demo.gif)

---

## Architecture & Workflow

```mermaid
graph TD
    A[".tickets/*.md<br/>(Plain Text & Git)"] --> B["Core Bash CLI<br/>(tk ready, tk start, tk dep)"]
    B --> C["Interactive Web UI<br/>(Kanban & DAG Mind Map)"]
    B --> D["AI Agent Skill<br/>(Automated 5-Step Loop)"]

    style A fill:#6366f1,stroke:#4f46e5,color:#fff
    style B fill:#3b82f6,stroke:#2563eb,color:#fff
    style C fill:#10b981,stroke:#059669,color:#fff
    style D fill:#a855f7,stroke:#9333ea,color:#fff
```

---

## Key Features

- **Plain Text Storage**: Tasks reside in `.tickets/*.md` files with YAML frontmatter, versioned directly in Git alongside the codebase.
- **DAG Dependency Tracking**: Native support for parent-child hierarchies, blockers, cycle detection, and automated downstream unblocking.
- **Portable Bash Core**: One Bash 3.2+ script using standard Unix tools; no Python or Node. `jq` is optional (only for `tk query` filters).
- **Safe for Concurrent Agents**: `tk start --claim` claims a ticket atomically under a per-ticket lock, exiting `3` if another agent got there first.
- **AI Agent Integration**: Deterministic 5-step operational loop, reusable agent skill (`agent-skill/tk/SKILL.md`), and machine-readable context endpoints.

---

## Official Plugins

Extend `ticket` with optional plugins discovered automatically via `$PATH`:

- **[Web UI (`tk webui`)](plugins/webui.md)**: Interactive 4-lane Kanban board, DAG Mind Map graph, table view, and background daemon manager.
- **[GitHub Import (`tk github`)](plugins/github.md)**: One-way import of GitHub issues and pull requests into local tickets.
- **[SCION Task Force (`tk scion-taskforce`)](plugins/scion-taskforce.md)**: Event-driven bridge from tickets to SCION coding agents: saving a `taskforce` ticket starts its SCION worker; humans review and close.

Learn how to write custom plugins in pure Bash or Python in the [Plugin Architecture Guide](plugins/architecture.md).

---

## Quick Installation

Install the zero-dependency Bash CLI or the full suite with the interactive Web UI:

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Full Suite (CLI + Web UI + Agent Skill) — default
./install.sh --full

# Core CLI only (pure Bash, no Python)
./install.sh --core
```

---

## Install Agent Skill via NPX

Install the agent skill for your AI coding assistant without cloning the repository:

```bash
npx github:msampathkumar/ticket agent-skill --install
```

---

## Machine-Readable Agent Documentation (llms.txt)

- [`/llms.txt`](llms.txt): Structured table of contents linking directly to all Markdown documentation files.
- [`/llms-full.txt`](llms-full.txt): Consolidated single-file documentation reference combining all specifications into one payload.
