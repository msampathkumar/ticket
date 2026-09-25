# tk - System & Data Specification

> **Specification Lifecycle Notice**  
> This specification document was formulated following the initial reference implementation of `tk`. Future architecture evolutions, format updates, and feature additions adhere to a **spec-driven development lifecycle**.

---

## 1. System Goals & Philosophy

`tk` is a **minimal, offline task tracker with dependency intelligence** designed for both human software engineers and autonomous AI coding agents.

### Core Principles
1. **Zero Global Database**: All state is stored locally within the repository in `.tickets/`.
2. **Plain-Text Transparency**: Every ticket is a human-readable Markdown file with a YAML frontmatter header.
3. **Graph-Centric (DAG)**: Native dependency tracking (`deps`) enables robust topological sorting, cycle detection, and ready-queue computation.
4. **Unix Portability**: The core CLI is implemented in POSIX-compliant Bash with `awk` and `sed`, requiring no runtimes or package managers.
5. **Decoupled Extensions**: Heavy features (Web UI, integrations) operate as independent, modular plugins discovering each other via `$PATH`.

---

## 2. Data Model & Ticket Schema

### 2.1 File Storage & Naming
- Directory: `.tickets/` (located in the repository root or discovered upwards in parent directories).
- File Naming: `<prefix>-<hash>.md` (e.g., `tic-6mex.md`, `msa-y8zi.md`).
  - Prefix defaults to 3 characters derived from the folder name or random alphanumeric.
  - Hash is a 4-character random alphanumeric string ensuring local uniqueness.

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
- **Cycle Detection**: Depth-First Search (DFS) traversal identifying circular references ($A \to B \to A$) across open tickets.

---

## 4. CLI Interface & Exit Codes

| Command | Description |
| :--- | :--- |
| `tk create <title> [options]` | Creates ticket, prints generated ID to stdout |
| `tk start <id>` | Sets status to `in_progress` |
| `tk close <id>` | Sets status to `closed` |
| `tk reopen <id>` | Sets status to `open` |
| `tk status <id> <status>` | Updates status directly (`open`, `in_progress`, `closed`) |
| `tk dep <id> <dep-id>` | Adds dependency relationship |
| `tk undep <id> <dep-id>` | Removes dependency relationship |
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
| `tk version` / `--version` | Prints version string (`tk version <version>`) |
| `tk help` | Displays available built-in commands and discovered plugins |

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
