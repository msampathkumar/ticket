---
title: Agent Skill
description: Autonomous AI agent integration skill for ticket (tk).
---

`ticket` provides an **Agent Skill** (`agent-skill/tk/SKILL.md`) that equips AI coding assistants with `tk` task management and DAG dependency intelligence.

---

## Overview

The agent skill instructs AI agents on:
- **Autonomous Execution**: Following the 5-step lifecycle (`tk ready` -> `tk start` -> `tk show` -> `tk add-note` -> `tk close`).
- **Dependency Awareness**: Managing parent-child tasks and blockers.
- **Review Audits**: Logging clear timestamped notes.

---

## Installation

Inspect the skill definition or install it locally, or install directly via `npx`:

```bash
# Inspect the skill definition
tk agent-skill

# Install to ~/.agents/skills/tk/SKILL.md using tk CLI
tk agent-skill --install

# Or install directly via npx without cloning
npx github:msampathkumar/ticket agent-skill --install
```

This installs the skill definition to `~/.agents/skills/tk/SKILL.md` where agents can discover and use it.

---

## Architecture Flow

```mermaid
graph TD
    A["AI Assistant / Agent"] -->|Reads Skill| B["agent-skill/tk/SKILL.md"]
    B -->|Discovers Actions| C["1. tk ready (Discover)"]
    B -->|Discovers Actions| D["2. tk start (id) (Claim)"]
    B -->|Discovers Actions| E["3. tk show (id) (Inspect)"]
    B -->|Discovers Actions| F["4. tk add-note (id) (Audit)"]
    B -->|Discovers Actions| G["5. tk close (id) (Resolve)"]
    
    style A fill:#6366f1,stroke:#4f46e5,color:#fff
    style B fill:#a855f7,stroke:#9333ea,color:#fff
    style C fill:#10b981,stroke:#059669,color:#fff
    style D fill:#3b82f6,stroke:#2563eb,color:#fff
    style E fill:#f59e0b,stroke:#d97706,color:#fff
    style F fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style G fill:#ef4444,stroke:#dc2626,color:#fff
```
