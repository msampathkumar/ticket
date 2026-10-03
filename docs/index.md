---
title: ticket (tk)
description: Minimal, dependency-aware task tracker. Built to scale agentic workflows.
---

# <img src="images/logo.svg" width="36" height="36" alt="tk logo" style="vertical-align: -6px; display: inline-block;" /> ticket (tk)

> Minimal, dependency-aware task tracker. Built to scale agentic workflows.

---

## Terminal Demo

![ticket CLI Demo](images/demo.gif)

---

## Architecture & Workflow

```mermaid
graph TD
    A[".tickets/*.md<br/>(Plain Text & Git)"] --> B["Core POSIX CLI<br/>(tk ready, tk start, tk dep)"]
    B --> C["Interactive Web UI<br/>(Kanban & DAG Mind Map)"]
    B --> D["AI Agent Skill<br/>(Automated 5-Step Loop)"]

    style A fill:#6366f1,stroke:#4f46e5,color:#fff
    style B fill:#3b82f6,stroke:#2563eb,color:#fff
    style C fill:#10b981,stroke:#059669,color:#fff
    style D fill:#a855f7,stroke:#9333ea,color:#fff
```

---

## Key Features

- **Plain Text Storage**: Tasks reside in `.tickets/*.md` files with YAML frontmatter, versioned directly in Git alongside codebase.
- **DAG Dependency Tracking**: Native support for parent-child hierarchies, blockers, cycle detection, and automated downstream unblocking.
- **Fast POSIX Core**: Core CLI runs on portable POSIX Bash with zero mandatory runtime dependencies (no Python or Node required for base operations).
- **AI Agent Integration**: Deterministic 5-step operational loop, reusable agent skill (`agent-skill/tk/SKILL.md`), and machine-readable context endpoints.

---

## Official Plugins

Extend `ticket` with modular plugins discovered automatically via `$PATH`:

- **[Web UI (`tk webui`)](plugins/webui.md)**: Interactive 4-lane Kanban board, DAG Mind Map graph, table view, and background daemon manager.
- **[GitHub Sync (`tk github`)](plugins/github.md)**: Bi-directional synchronization between local markdown tickets and GitHub issues/pull requests.
- **[SCION Task Force (`tk scion-taskforce`)](plugins/scion-taskforce.md)**: Autonomous multi-agent worker orchestration daemon with human review checkpoints.

Learn how to write custom plugins in pure Bash or Python in the [Plugin Architecture Guide](plugins/architecture.md).

---

## Quick Installation

Install the zero-dependency Bash CLI or the full suite with the interactive Web UI:

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Full Suite (CLI + Web UI + Agent Skill) — default
./install.sh --full

# Core CLI Only (Pure Bash, zero Python dependencies)
./install.sh --core
```

---

## Install Agent Skill via NPX

Install the agent skill for your AI coding assistant without cloning the repo:

```bash
npx github:msampathkumar/ticket agent-skill --install
```

---

## Machine-Readable Agent Documentation (llms.txt)

- [`/llms.txt`](llms.txt): Structured table of contents linking directly to all Markdown documentation files.
- [`/llms-full.txt`](llms-full.txt): Consolidated single-file documentation reference combining all specifications into one payload.
