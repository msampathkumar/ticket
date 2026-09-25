---
name: tk
description: Manage local tickets, tasks, bugs, dependencies, and project planning using the tk minimal ticket system and tk-webui. Use when creating, updating, resolving, linking, checking blocked/ready tasks, or managing DAG dependency trees in projects with a .tickets repository.
---

# tk - Agent Skill Guide

This skill equips agents to interact with **`tk`**, a fast, git-backed ticket tracking system designed for AI agents and human developers.

## Overview

Tickets are stored as Markdown files with YAML frontmatter in a `.tickets/` directory at the project root. All operations are local, plain-text, and trackable with git.

## Core Commands Reference

### 1. Ticket Lifecycle
- **Create**:
  ```bash
  tk create "Feature title" -t feature -p 2 -d "Detailed description" --tags "ui,backend"
  ```
  Options:
  - `-t, --type`: `bug` | `feature` | `task` | `epic` | `chore` (default: `task`)
  - `-p, --priority`: `0` (critical) to `4` (trivial) (default: `2`)
  - `-a, --assignee`: Assignee name / username
  - `-d, --description`: Description text
  - `--design`: Architecture / design notes
  - `--acceptance`: Acceptance criteria checklist
  - `--parent`: Parent ticket ID for subtasks
  - `--external-ref`: GitHub issue / PR / JIRA reference (e.g. `gh-42`)
  - `--tags`: Comma-separated tags

- **Inspect**:
  ```bash
  tk show <ticket-id>
  ```

- **Update**:
  ```bash
  tk update <ticket-id> -p 1 -a "Developer" -d "New details" --tags "urgent"
  ```

- **Status transitions**:
  ```bash
  tk start <ticket-id>     # In progress
  tk close <ticket-id>     # Closed
  tk reopen <ticket-id>    # Back to open
  tk status <ticket-id> <open|in_progress|closed>
  ```

- **Add Review / Progress Note**:
  ```bash
  tk add-note <ticket-id> "Review feedback or progress update"
  ```

### 2. Dependency Management & DAG Queries
- **Add dependency**:
  ```bash
  tk dep <ticket-id> <blocker-id>   # <ticket-id> now depends on <blocker-id>
  ```
- **Remove dependency**:
  ```bash
  tk undep <ticket-id> <blocker-id>
  ```
- **Show dependency tree**:
  ```bash
  tk dep tree <ticket-id>
  ```
- **Detect dependency cycles**:
  ```bash
  tk dep cycle
  ```
- **Query Ready / Unblocked tasks**:
  ```bash
  tk ready       # Lists tickets whose dependencies are all closed
  ```
- **Query Blocked tasks**:
  ```bash
  tk blocked     # Lists tickets waiting on unresolved dependencies
  ```

### 3. Launching the Web UI
```bash
tk webui [optional-dir]
```
Launches the 4-lane Kanban, Table view, interactive DAG Mind Map, and Timeline views at `http://127.0.0.1:8000`.

## Agent Best Practices

1. **Check `tk ready` before picking up work**:
   Always run `tk ready` to find actionable, unblocked tickets rather than picking blocked ones.
2. **Start the ticket**:
   Run `tk start <id>` when beginning work so other team members and agents know it's in progress.
3. **Document review notes**:
   Use `tk add-note <id> "..."` when submitting code for review or recording architectural findings.
4. **Close upon completion**:
   Run `tk close <id>` when verification and tests pass.
