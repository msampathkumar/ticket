---
title: Command Reference
description: Comprehensive reference for all core ticket (tk) CLI commands.
---

The `tk` CLI provides commands for task lifecycle management, dependency tracking, and querying.

---

## Core CRUD & Lifecycle

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk init [path]` | Initialize `.tickets` repository | `tk init` |
| `tk create [title]` | Create a new ticket (returns ID) | `tk create "Fix login bug" -p 0 -t bug` |
| `tk show <id>` | Display full ticket details | `tk show tic-c83r` |
| `tk update <id>` | Update title, description, priority, tags | `tk update tic-c83r -p 1 --tags urgent` |
| `tk start <id>` | Transition ticket to `in_progress` | `tk start tic-c83r` |
| `tk close <id>` | Transition ticket to `closed` | `tk close tic-c83r` |
| `tk reopen <id>` | Transition ticket back to `open` | `tk reopen tic-c83r` |
| `tk edit <id>` | Open ticket markdown file in `$EDITOR` | `tk edit tic-c83r` |

---

## Dependency Intelligence

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk dep <id> <dep-id>` | Add dependency (`id` depends on `dep-id`) | `tk dep tic-2 tic-1` |
| `tk undep <id> <dep-id>` | Remove dependency relationship | `tk undep tic-2 tic-1` |
| `tk dep tree <id>` | Display recursive dependency tree | `tk dep tree tic-1` |
| `tk dep cycle` | Detect dependency cycles across open tickets | `tk dep cycle` |
| `tk ready` | List unblocked actionable tasks | `tk ready` |
| `tk blocked` | List tasks waiting on unresolved dependencies | `tk blocked` |

---

## Querying & Listing

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk ls` | List tickets (hides closed, limit 10) | `tk ls -s open -p 1` |
| `tk query [jq]` | Output tickets as JSON, filterable with `jq` | `tk query '.[] | select(.priority==0)'` |
| `tk find <term>` | Full-text search across all tickets | `tk find "authentication"` |
| `tk add-note <id> [text]` | Append timestamped audit note | `tk add-note tic-1 "Tested successfully"` |
