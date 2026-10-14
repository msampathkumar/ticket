# tk - System & Data Specification

> **Specification Lifecycle**  
> Architecture changes, format updates, and new features follow a **spec-driven development lifecycle**.

---

## 1. System Goals & Philosophy

`tk` is a **minimal, dependency-aware task tracker. Built to scale agentic workflows.**

### Scope
`tk` core is a minimal task queue that many agents and humans can share through plain files. It provides:

- Plain-text tickets (`.tickets/*.md`) that version and merge through Git; Git itself is optional.
- DAG dependencies with cycle detection, and a deterministic ready queue (`tk ready`).
- Atomic claiming (`tk start --claim`) and per-ticket locks for concurrent agents.
- Post-write hooks (`.tickets/.hooks/post-write.d/`) as the single extension point for reacting to changes.

Everything else lives in optional plugins, discovered on `$PATH` as `tk-<cmd>` (see Section 5): the Web UI (`tk webui`), GitHub sync (`tk github`), and agent dispatch (`tk scion-taskforce`, an event-driven bridge from ticket hooks to Scion, which runs the agents).

### Core Principles
1. **Zero Database**: State is stored locally in `.tickets/*.md`.
2. **Plain-Text Transparency**: Every ticket is a Markdown file with YAML frontmatter.
3. **DAG-Driven**: Native dependency tracking (`deps`) enables topological sorting, cycle detection, and ready-queue computation.
4. **Unix Portability**: Core CLI is a single portable Bash script (Bash 3.2+, macOS and Linux) using standard tools (`awk`, `sed`, `grep`, `find`, `mkdir`); no other runtime required. It is Bash, not POSIX `sh`.
5. **Decoupled Extensions**: Web UI and external integrations operate as modular plugins.

### Non-goals
Core will not:

- Use a database, server, or background daemon. Hooks run once per write and exit.
- Access the network. Sync with GitHub or other services belongs to plugins.
- Orchestrate agents (spawning, scheduling, assigning, or supervising workers). Core supplies the shared queue, claims, and hooks; orchestration belongs to plugins and the tools they drive.
- Require a runtime beyond Bash and standard Unix tools. `jq` is optional and only needed for `tk query <filter>`; Python is used only by plugins.
- Require Git. Tickets are plain files; Git is the recommended way to share and review them.
- Render a UI. The terminal output is plain text; visual views belong to `tk webui`.

---

## 2. Data Model & Ticket Schema

### 2.1 File Storage & Naming
- Directory: `.tickets/` (located in the repository root or discovered upwards in parent directories).
- File Naming: `<prefix>-<hash>.md` (e.g., `tic-6mex2q.md`, `msa-y8zi0k.md`).
  - Prefix defaults to 3 characters derived from the folder name or random alphanumeric. Only ASCII letters, digits and `.` are kept; a folder name with none falls back to `tk`.
  - Hash is a random lowercase alphanumeric string from `/dev/urandom` (fallback: `$RANDOM`), 6 characters by default (`TK_ID_HASH_LENGTH`, 4-32). Lowercase keeps IDs distinct on case-insensitive filesystems.
  - Generation retries if `<id>.md` already exists locally. Across branches, 6 characters (36^6 ≈ 2.2 × 10^9 values) keep the collision chance for 1,000 tickets near 0.02%, versus about 25% with 4 characters.
  - Older 4-character IDs (e.g., `tic-6mex`) remain valid; exact and partial ID resolution work for both lengths.

### 2.2 YAML Frontmatter Schema

Each ticket file begins with a YAML header delimited by `---`:

```yaml
---
id: string          # Unique ticket identifier, e.g. tic-6mex (Required)
status: enum        # open | in_progress | closed (Required)
deps: list[string]  # Array of ticket IDs this ticket depends on (Required)
links: list[string] # Array of related ticket IDs (symmetric) (Optional)
created: ISO-8601   # Timestamp of ticket creation (e.g. 2026-09-25T10:01:06Z) (Required)
type: enum          # bug | feature | task | epic | chore (Default: task)
priority: integer   # 0 (Critical) to 4 (Trivial) (Default: 2)
assignee: string    # Assignee name or git username (Optional)
tags: list[string]  # Array of tag strings (Optional)
parent: string      # Parent ticket ID if this ticket is a subtask (Optional)
external_ref: string# External issue/PR reference, e.g. gh-123 (Optional)
---
```

### 2.3 Markdown Body Structure

Following the frontmatter, the Markdown body contains:

```markdown
# <Title>

<Description text...>

## Design Notes
<Architecture or design thoughts...>

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

## Review Notes / Audit Trail
<!-- Timestamped review comments appended by tk add-note -->
### Note (2026-09-25T10:30:00Z)
<Comment content>
```

---

## 3. Dependency DAG Semantics

### 3.1 Directed Acyclic Graph (DAG) Rules
- A dependency `A -> B` (`deps: [B]`) means **Ticket A is blocked by Ticket B**.
- Ticket A cannot be resolved or considered "Ready" until Ticket B is in `closed` status.
- Symmetric links (`links: [B]`) denote relational associations without blocking semantics.

### 3.2 State Queries
- **Ready Queue**: All non-closed tickets whose dependencies are either empty or completely satisfied by tickets in `status: closed`.
- **Blocked Queue**: All non-closed tickets where at least one dependency in `deps` is in `status: open` or `status: in_progress`.
- **Cycle Detection**: Depth-First Search (DFS) traversal identifying circular references (`A -> B -> A`) across open tickets.

---

## 4. CLI Interface & Exit Codes

| Command | Description |
| :--- | :--- |
| `tk init [path]` | Initializes `.tickets/` tracking repository |
| `tk create <title> [options]` | Creates ticket, prints generated ID to stdout |
| `tk start <id>` | Sets status to `in_progress` |
| `tk start <id> --claim [--assignee X]` | Atomically sets status `in_progress` and `assignee` (default: `git config user.name`, else `$USER`); fails with exit code `3` if already `in_progress` for a different assignee |
| `tk close <id>` | Sets status to `closed` |
| `tk reopen <id>` | Sets status to `open` |
| `tk status <id> <status>` | Updates status directly (`open`, `in_progress`, `closed`) |
| `tk dep <id> <dep-id>` | Adds dependency relationship |
| `tk undep <id> <dep-id>` | Removes dependency relationship |
| `tk link <id> <link-id>` | Adds symmetric relational link between tickets |
| `tk unlink <id> <link-id>` | Removes symmetric relational link between tickets |
| `tk dep tree <id>` | Prints hierarchical ASCII dependency tree |
| `tk dep cycle` | Traverses graph and outputs detected cycles |
| `tk ready` | Lists unblocked, actionable tickets |
| `tk blocked` | Lists blocked tickets with unresolved blockers |
| `tk closed [--limit=N]` | Lists recently closed tickets |
| `tk ls` / `tk list [options]` | Lists tickets (default: hides closed, limit 10, with filters) |
| `tk edit <id>` | Opens ticket in `$EDITOR` |
| `tk query [jq-filter]` | Outputs tickets as JSON lines, with optional jq filter |
| `tk find <search-term>` | Case-insensitive text search across tickets |
| `tk show <id>` | Displays ticket metadata and full markdown body |
| `tk update <id> [options]` | Updates fields (title, desc, priority, tags, etc.) |
| `tk add-note <id> [text]` | Appends timestamped note |
| `tk agent-skill [--install]` | Displays or installs agent skill to `~/.agents/skills/tk/` |
| `tk version` / `--version` | Prints version, description, and license information |
| `tk help` | Displays available built-in commands and discovered plugins |

### 4.1 Exit Codes

| Code | Meaning |
| :--- | :--- |
| `0` | Success |
| `1` | Error (usage, ticket not found, invalid value) |
| `3` | Claim lost: `tk start --claim` found the ticket `in_progress` for another assignee |
| `4` | Lock timeout: another `tk` process held the ticket lock for longer than `TK_LOCK_TIMEOUT` |

### 4.2 Ticket Locks & Claiming

Status writes (`start`, `close`, `reopen`, `status`) and claims run under a per-ticket lock, so concurrent agents cannot interleave a read-check-write on the same ticket.

- **Mechanism**: `mkdir $TICKETS_DIR/.locks/<id>.lock` (atomic on POSIX filesystems; no `flock` dependency). The lock holds an `owner` file: `<pid> <host> <epoch>`. It is removed on exit, including on error or `SIGINT`/`SIGTERM`.
- **Waiting**: a busy lock is retried every 0.1s for up to `TK_LOCK_TIMEOUT` seconds (default `10`), then the command exits `4`.
- **Stale locks**: a lock is stale when its owner pid no longer runs on the same host, or it is older than `TK_LOCK_STALE_SECONDS` (default `60`). A waiter renames a stale lock aside (only one waiter wins the rename) and deletes it. Locks from crashed processes on other hosts (shared network filesystems) expire by age only. To clear one manually: `rm -rf .tickets/.locks/<id>.lock`.
- **Claim rule**: `--claim` succeeds if the ticket is not `in_progress`, has no assignee, or is already assigned to the claimant (re-claiming is idempotent). Agents sharing one identity must pass distinct `--assignee` values.
- **Scope**: locks coordinate `tk` processes sharing one `.tickets/` directory. Claims across separate Git clones are reconciled through Git, not by this lock.
- **Git**: lock files never belong in Git. `tk init` adds `.locks/` and `.hooks/hooks.log` to `.tickets/.gitignore` (appending only missing lines), and the first lock writes a self-ignoring `.tickets/.locks/.gitignore` (`*`), which also covers repositories initialized earlier. Re-running `tk init` in an existing repository is safe.
- Plain `tk start <id>` is unchanged: it sets `in_progress` without checking or changing the assignee.

---

## 5. Plugin & Extension Protocol

1. Any executable named `tk-<command>` or `ticket-<command>` in `$PATH` or located within `plugins/<command>/` is automatically invoked when running `tk <command>`.
2. When invoked, the core CLI exports:
   - `TICKETS_DIR`: Absolute path to the resolved `.tickets` directory.
   - `TK_SCRIPT`: Absolute path to the root `tk` executable.
3. Plugins must conform to **[PLUGIN_SPEC.md](PLUGIN_SPEC.md)**:
   - Directory isolation: `plugins/<plugin-name>/` containing executable and `<PLUGIN-NAME>-SPEC.md`.
   - Optionality: Except for `tk-webui`, all plugins are optional.
   - Metadata discovery: `# tk-plugin: <description>` comment in header or `--tk-describe` flag for `tk help` discovery.
   - Version contract: `--version` flag for standardized version reporting.

### 5.1 Post-Write Hooks

After a successful write, `tk` runs every executable file in `$TICKETS_DIR/.hooks/post-write.d/` (lexical order). Plugins use this to react to saves without polling; `tk scion-taskforce init` installs one.

- **Events** (`TK_EVENT`): `create`, `start`, `close`, `reopen`, `status`, `update`, `add-note`, `dep`, `undep`, `link`, `unlink`, `edit`. Read-only commands, `dep tree`, `dep cycle`, and failed writes fire nothing.
- **Environment**: `TK_EVENT`, `TK_TICKET_ID` (full ID), `TK_TICKET_FILE`, `TICKETS_DIR` (absolute), `TK_SCRIPT`, `TK_HOOK_DEPTH=1`.
- **Execution**: background (`nohup`) by default; inline when `TK_HOOKS_SYNC=1`. Output is appended to `.tickets/.hooks/hooks.log`. Hook exit codes never change the `tk` exit code.
- **Recursion guard**: hooks are skipped when `TK_HOOK_DEPTH` is set, so a hook calling `tk` does not re-trigger itself. Set `TK_NO_HOOKS=1` to disable hooks for one command.
- The Web UI writes through the `tk` CLI, so its saves fire the same hooks. Hand edits and `git pull` do not.
