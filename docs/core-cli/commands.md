---
title: Command Reference
description: Comprehensive reference for all core ticket (tk) CLI commands.
---

The `tk` CLI covers the ticket lifecycle, dependency tracking, and querying. Every command accepts a full or partial ticket ID (`tk show 5c4` matches `nw-5c46a1`). Run `tk help` for the built-in summary and the list of installed plugins.

---

## Repository

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk init [dir]` | Create `.tickets/` with a closed setup ticket and `.tickets/.gitignore`. Safe to re-run. | `tk init` |
| `tk uninit [dir]` | Delete the `.tickets/` directory and every ticket in it. No confirmation. | `tk uninit` |

`tk create` also initializes `.tickets/` (with the setup ticket) in the current directory when none is found.

---

## Create, Show, Update

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk create [title] [options]` | Create a ticket and print its ID | `tk create "Fix login bug" -p 0 -t bug` |
| `tk show <id>` | Print the ticket (uses `$TICKET_PAGER` or `$PAGER` on a terminal) | `tk show tic-c83r2a` |
| `tk update <id> [options]` | Update fields in place | `tk update tic-c83r2a -p 1 --tags urgent` |
| `tk edit <id>` | Open the ticket file in `$EDITOR` | `tk edit tic-c83r2a` |
| `tk add-note <id> [text]` | Append a timestamped note; reads stdin when `text` is omitted | `echo "Done" \| tk add-note tic-1` |

**`create` options**

| Option | Meaning | Default |
| :--- | :--- | :--- |
| `-d`, `--description` | Description text | |
| `--design` | Design notes | |
| `--acceptance` | Acceptance criteria | |
| `-t`, `--type` | `bug`, `feature`, `task`, `epic`, `chore` | `task` |
| `-p`, `--priority` | `0` (highest) to `4` | `2` |
| `-a`, `--assignee` | Assignee | `git config user.name` |
| `--external-ref` | External reference, e.g. `gh-123`, `JIRA-456` | |
| `--parent` | Parent ticket ID | |
| `--tags` | Comma-separated tags | |

**`update` options**: `--title`, `-d`/`--description`, `-p`/`--priority`, `-t`/`--type`, `-a`/`--assignee`, `--tags`, `--design`, `--acceptance`, `--parent`, `--external-ref`.

Values are stored verbatim, including `/`, `&`, `\` and `|`. Frontmatter fields (assignee, tags, external ref, parent, and other single-line values) reject newlines with an error. See [SPEC §2.4](../SPEC.md).

---

## Status and Claiming

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk start <id>` | Set status to `in_progress` | `tk start tic-c83r2a` |
| `tk start <id> --claim [--assignee X]` | Set `in_progress` and the assignee in one locked step | `tk start tic-c83r2a --claim --assignee agent-2` |
| `tk close <id>` | Set status to `closed` | `tk close tic-c83r2a` |
| `tk reopen <id>` | Set status to `open` | `tk reopen tic-c83r2a` |
| `tk status <id> <status>` | Set `open`, `in_progress`, or `closed` | `tk status tic-c83r2a open` |

`--claim` defaults the assignee to `git config user.name`, else `$USER`. It fails with exit code `3` when the ticket is already `in_progress` for a different assignee; re-claiming your own ticket succeeds. Agents that share one identity must pass distinct `--assignee` values.

Status writes and claims run under a per-ticket lock in `.tickets/.locks/`. If another `tk` process holds the lock for longer than `TK_LOCK_TIMEOUT` seconds (default `10`), the command exits `4`. See [SPEC §4.2](../SPEC.md).

---

## Dependencies and Links

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk dep <id> <dep-id>` | `id` depends on `dep-id`; rejects self-dependencies and cycles (exit `1`) | `tk dep tic-2 tic-1` |
| `tk undep <id> <dep-id>` | Remove a dependency | `tk undep tic-2 tic-1` |
| `tk dep tree [--full] <id>` | Print the dependency tree; `--full` disables deduplication | `tk dep tree tic-1` |
| `tk dep cycle` | Report dependency cycles among open tickets | `tk dep cycle` |
| `tk link <id> <id> [id...]` | Link tickets symmetrically (no blocking) | `tk link tic-1 tic-2 tic-3` |
| `tk unlink <id> <target-id>` | Remove a link | `tk unlink tic-1 tic-2` |

---

## Queues and Listing

| Command | Description | Example |
| :--- | :--- | :--- |
| `tk ready [-a X] [-T X]` | Open or in-progress tickets whose dependencies are all closed | `tk ready -T backend` |
| `tk blocked [-a X] [-T X]` | Open or in-progress tickets with unresolved dependencies | `tk blocked` |
| `tk closed [--limit=N] [-a X] [-T X]` | Recently closed tickets, by file mtime (default 20) | `tk closed --limit=5` |
| `tk ls`, `tk list [options]` | List tickets; hides closed, limit 10 | `tk ls -s open -p 1` |
| `tk find <search-term>` | Search text across tickets | `tk find "authentication"` |
| `tk query [jq-filter]` | Print tickets as JSON lines; the filter needs `jq` | `tk query '.priority == "0"'` |

`-a` filters by assignee, `-T` by tag.

**`ls` options**: `-s`/`--status` (`open`, `in_progress`, `closed`, `all`), `-a`/`--assignee`, `-t`/`--type`, `-p`/`--priority`, `-T`/`--tag`, `-n`/`--limit` (default 10), `--full` (no limit), `--all` (all statuses, no limit).

---

## Other

| Command | Description |
| :--- | :--- |
| `tk agent-skill [--install] [--path]` | Print the agent skill, install it to `~/.agents/skills/tk/SKILL.md`, or print its installed path |
| `tk version`, `--version`, `-v` | Print version and project information |
| `tk help`, `--help`, `-h` | Print built-in commands and installed plugins |
| `tk super <cmd> [args]` | Run a built-in command, bypassing any plugin with the same name |

A plugin named `tk-<cmd>` or `ticket-<cmd>` takes precedence over a built-in `<cmd>`; see [Plugin Architecture](../plugins/architecture.md).

---

## Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Success |
| `1` | Error: usage, ticket not found, invalid or multi-line value, or a ticket file that cannot be written |
| `3` | Claim lost: `tk start --claim` found the ticket `in_progress` for another assignee |
| `4` | Lock timeout: another `tk` process held the ticket lock longer than `TK_LOCK_TIMEOUT` |

A failed write prints `Error: cannot write ticket file '<path>'`, prints no ticket ID, and fires no hooks.
