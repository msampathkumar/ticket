# tk - AI Agent Guidelines & Integration Guide

This document outlines best practices and rules for AI coding assistants and autonomous agents (e.g. Antigravity, Claude, Cursor, Copilot, Gemini CLI) when operating within repositories tracked by `tk`.

---

## 1. Why `tk` is Ideal for AI Agents

- **File-Centric State**: AI agents can read and write tickets using standard file and CLI tools without managing database connections.
- **Topological Dependency Order**: `tk ready` prevents agents from picking up blocked tasks out of order.
- **Audit Trails in Markdown**: Agents can record reasoning, test results, and review comments directly in the ticket file.

---

## 2. Standard Workflow for AI Agents

```mermaid
flowchart TD
    A[Agent scans ready tasks via `tk ready`] --> B[Select next actionable ticket]
    B --> C[Mark in-progress via `tk start <id>`]
    C --> D[Implement & verify code changes]
    D --> E[Append review notes via `tk add-note <id> "..."]
    E --> F[Close ticket via `tk close <id>`]
```

### Step 1: Discover Actionable Work
Run `tk ready` to list open tickets whose dependencies are already resolved:
```bash
tk ready
```

### Step 2: Mark Task in Progress
Inform human developers and other agents that the ticket is being worked on:
```bash
tk start <ticket-id>
```

### Step 3: Check Subtasks and Design Requirements
View ticket specifications, design notes, and acceptance checklist:
```bash
tk show <ticket-id>
```

### Step 4: Record Progress & Notes
Append timestamped notes detailing the verification results or implementation choices:
```bash
tk add-note <ticket-id> "Implemented visual tree with horizontal orientation and verified locally."
```

### Step 5: Mark Complete
Close the ticket after test execution:
```bash
tk close <ticket-id>
```

---

## 3. Subtask Decomposition Pattern

When an agent encounters a large epic or complex feature:
1. Create subtasks with `--parent <epic-id>`:
   ```bash
   tk create "Implement backend API endpoint" --parent <epic-id> -t task
   tk create "Build frontend UI modal" --parent <epic-id> -t task
   ```
2. Wire dependencies between subtasks:
   ```bash
   tk dep <frontend-id> <backend-id>
   ```

---

## 4. Agent Skill Installation

Agents supporting custom skills can install the `tk` skill definition directly into `~/.agents/skills/tk/SKILL.md`:
```bash
./install.sh --skill
```
