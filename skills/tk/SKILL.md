---
name: tk
description: Manage local tickets, tasks, bugs, dependencies, and project planning using the tk minimal, offline task tracker with dependency intelligence and tk-webui.
---

# tk - Agent Skill Guide

This skill equips agents to interact with **`tk`**, a **minimal, offline task tracker with dependency intelligence** designed for AI agents and human developers.

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

- **List & Filter Tickets**:
  ```bash
  tk ls                          # List tickets (hides closed, limit 10 by default)
  tk ls --full                   # List all open tickets without limit
  tk ls --status=closed          # List closed tickets
  tk ls -a "Developer" --type bug # Filter by assignee and type
  ```

- **Search & Query**:
  ```bash
  tk find "search query"         # Search text across title, desc, notes
  tk query                       # Stream tickets as JSON lines
  tk query '.priority == "0"'    # Query with jq filter
  tk edit <ticket-id>            # Open in $EDITOR
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
- **Recently closed tasks**:
  ```bash
  tk closed      # Lists recently closed tickets
  ```

### 3. Interactive Web UI & Background Server
```bash
# Foreground server on port 8475 (ASCII: T=84, K=75)
tk webui [optional-dir]

# Background daemon server management
tk webui server start [dir]    # Start daemon in background
tk webui server status         # Check status, URL, and PID
tk webui server stop           # Stop background daemon
tk webui server restart [dir]  # Restart background daemon
```

### 4. GitHub Synchronization Plugin
```bash
tk github sync                 # Sync open GitHub issues & PRs to .tickets/
tk github sync --issues        # Sync only issues
tk github sync --prs           # Sync only PRs
tk github list                 # List synced GitHub tickets
tk github unsync -y            # Remove synced tickets
```

## Agent Best Practices

1. **Check `tk ready` before picking up work**:
   Always run `tk ready` to find actionable, unblocked tickets rather than picking blocked ones.
2. **Start the ticket**:
   Run `tk start <id>` when beginning work so other team members and agents know it's in progress.
3. **Decompose complex features**:
   Create subtasks with `tk create "<title>" --parent <epic-id>` and wire `tk dep <child> <blocker>`.
4. **Document review notes**:
   Use `tk add-note <id> "..."` when submitting code for review or recording architectural findings.
5. **Close upon completion**:
   Run `tk close <id>` when verification and tests pass.
