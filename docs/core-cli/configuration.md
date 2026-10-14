---
title: Core CLI Configuration
description: Environment variables, directory discovery, and default settings for ticket (tk).
---

`ticket` (`tk`) has no database, server, or config file. Behaviour is set through environment variables, and state lives in `.tickets/`.

---

## Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `TICKETS_DIR` | Path to the `.tickets` directory. Overrides discovery. | Discovered upwards from `$PWD` |
| `EDITOR`, `VISUAL` | Editor for `tk edit` (`EDITOR` wins over `VISUAL`). | `nano` |
| `TICKET_PAGER`, `PAGER` | Pager for `tk show` when stdout is a terminal (`TICKET_PAGER` wins). | None (no pager) |
| `TK_ID_HASH_LENGTH` | Length of the random part of new ticket IDs (4-32). | `6` |
| `TK_LOCK_TIMEOUT` | Seconds to wait for a busy ticket lock before exiting `4`. | `10` |
| `TK_LOCK_STALE_SECONDS` | Age after which a lock is treated as stale and removed. | `60` |
| `TK_NO_HOOKS` | Skip post-write hooks for the command. See [SPEC §5.1](../SPEC.md). | Unset (hooks run) |
| `TK_HOOKS_SYNC` | Run post-write hooks inline instead of in the background. | Unset (background) |
| `AGENTS_SKILLS_DIR` | Target directory for `tk agent-skill --install`. | `$HOME/.agents/skills/tk` |
| `TK_SCRIPT` | Path to the `tk` executable; exported to plugins and hooks. | Set by `tk` |

---

## Directory Discovery

1. If `TICKETS_DIR` is set, `tk` uses it. Read commands fail if that directory does not exist.
2. Otherwise `tk` walks up from `$PWD` to `/` and uses the first `.tickets/` directory it finds. Git is not consulted.
3. If none is found, `tk create`, `tk init` and `tk uninit` work on `./.tickets`; `tk create` and `tk init` create it. Other commands exit `1` with `Error: no .tickets directory found`.

`tk init` (also run by `tk create` when it initializes `.tickets/`) records the project in `~/.local/state/tk/projects.json`, which the Web UI uses for its project list.

---

## File Layout

```
my-project/
├── .tickets/
│   ├── .gitignore            # .locks/ and .hooks/hooks.log (written by tk init)
│   ├── .locks/               # Per-ticket lock dirs, self-ignoring (runtime only)
│   ├── .hooks/
│   │   ├── post-write.d/     # Executable post-write hooks
│   │   └── hooks.log         # Hook output (runtime only)
│   ├── myp-a1b2c3.md
│   └── myp-d4e5f6.md
├── src/
└── README.md
```

Commit the ticket files; `.tickets/.gitignore` keeps locks and the hook log out of Git.

### Ticket File

IDs are `<prefix>-<hash>`: a prefix derived from the folder name (ASCII letters, digits and `.` only; `tk` if none remain) and a random lowercase alphanumeric hash, 6 characters by default. Older 4-character IDs remain valid.

```markdown
---
id: myp-a1b2c3
status: open
deps: [myp-d4e5f6]
links: []
created: 2026-10-03T12:00:00Z
type: task
priority: 2
assignee: developer
external-ref: gh-42
parent: myp-0e1f2a
tags: [backend, api]
---
# Ticket Title

Description text explaining requirements and context.

## Design

Architectural decisions, trade-offs, and technical notes.

## Acceptance Criteria

- [ ] Feature implemented
- [ ] Unit tests pass

## Notes

**2026-10-03T12:30:00Z**

Timestamped progress update or review note.
```

Values are written verbatim and YAML-quoted only when plain YAML would misread them. Frontmatter values must be a single line; a value containing a newline is rejected with exit code `1`. See [SPEC §2](../SPEC.md).

---

## Defaults

- **Priority**: `2` (range `0` = highest to `4` = lowest).
- **Type**: `task`.
- **Assignee**: `git config user.name` when `-a` is not given.
- **Listing**: `tk ls` hides closed tickets and shows 10 items. Use `--full` (no limit), `--all` (all statuses, no limit), `-s all`, or `tk closed`.

---

## Optional Tools

The core needs only Bash 3.2+ and standard Unix tools. These are used when present:

| Tool | Used for |
| :--- | :--- |
| `jq` | `tk query <filter>`; without it, only unfiltered `tk query` works |
| `rg` (ripgrep) | Faster `tk find`; falls back to `grep` |
| `git` | Default assignee (`user.name`); sharing tickets |
