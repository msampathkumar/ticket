---
title: Core CLI Configuration
description: Environment variables, directory discovery, and default settings for ticket (tk).
---

`ticket` (`tk`) is designed around a zero-database, offline-first architecture. It requires no configuration daemon or centralized database server. Configuration is managed through environment variables and Git repository state.

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TICKETS_DIR` | Absolute path to the active `.tickets` directory. Overrides automatic discovery. | Auto-detected (scanned upwards from `$PWD` to Git root) |
| `EDITOR` / `VISUAL` | Text editor invoked when editing tickets with `tk edit <id>`. | System default, fallback to `vim` |
| `AGENTS_SKILLS_DIR` | Target installation directory when running `tk agent-skill --install`. | `$HOME/.agents/skills/tk` |
| `TK_SCRIPT` | Path to the root `tk` executable. Automatically exported to plugins. | Auto-detected path to `tk` |
| `NO_COLOR` | Disables ANSI color output when set to any non-empty value. | Unset (colors enabled) |

---

## Directory Discovery Logic

When you run any `tk` command:
1. `tk` checks if `TICKETS_DIR` is set in your environment. If set and valid, it is used immediately.
2. Otherwise, `tk` starts at the current working directory (`$PWD`) and scans upwards until it finds a directory named `.tickets/`.
3. If no `.tickets/` directory is found, `tk` checks for `.git/` to determine the project root.
4. If neither is found, `tk create` offers to automatically run `tk init` to bootstrap the task tracker.

---

## File Layout & Storage Model

All tasks are stored as plain text Markdown files with YAML frontmatter inside `.tickets/`:

```
my-project/
├── .git/
├── .tickets/
│   ├── tic-a1b2.md
│   ├── tic-c3d4.md
│   └── tic-e5f6.md
├── src/
└── README.md
```

### Ticket Schema
Every ticket file (`.tickets/tic-<id>.md`) follows this canonical structure:

```yaml
---
id: tic-a1b2
status: open
deps: [tic-prev]
links: []
created: 2026-10-03T12:00:00Z
type: task
priority: 2
assignee: developer
tags: [backend, api]
external_ref: gh-issue-42
parent: tic-epic1
---
# Ticket Title

Description text explaining requirements and context.

## Design Notes
Architectural decisions, trade-offs, and technical notes.

## Acceptance Criteria
- [ ] Feature implemented
- [ ] Unit tests pass

## Notes
**2026-10-03T12:30:00Z**
Timestamped progress update or review audit trail.
```

---

## CLI Defaults & Filtering

- **Priority**: Defaults to `2` (range: `0` = urgent/critical, `1` = high, `2` = medium, `3` = low, `4` = backlog).
- **Listing Limit**: `tk ls` defaults to 10 items to prevent terminal flooding. Use `--full` or `--all` for unlimited listings.
- **Closed Tickets**: `tk ls` hides closed tickets by default. Use `-s all` or `tk closed` to inspect completed tasks.
