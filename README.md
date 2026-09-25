# ticket (tk)

The git-backed issue tracker for AI agents and developers, featuring an ultra-fast CLI and an optional modern Kanban & review dashboard.

Rooted in the Unix Philosophy, `tk` is inspired by Joe Armstrong's [Minimal Viable Program](https://joearms.github.io/published/2014-06-25-minimal-viable-program.html) with quality-of-life features for managing and querying complex issue dependency graphs.

---

## ⚡ Quick Install

You can install either just the lightweight, zero-dependency Bash CLI, or the complete suite with the interactive Web UI.

### 1. Using the Modular Installer Script

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Option A: Full Suite (CLI + Interactive Web UI)
./install.sh --full

# Option B: Core CLI Only (Zero Python dependencies, pure Bash)
./install.sh --core

# Option C: Web UI Plugin Only
./install.sh --webui
```

This installs binaries directly to `~/.local/bin/` (`tk` and `tk-webui`). Make sure `~/.local/bin` is in your `$PATH`.

### 2. Run Locally (Without Installing)

You can launch and try the Web UI immediately without global installation:

```bash
./run.sh [optional-project-path]
```

---

## 🚀 Key Features

### 🖥️ Core CLI (`tk`)
- **Git-Backed**: Tickets are stored as human-readable Markdown files with YAML frontmatter inside `.tickets/`.
- **Dependency Tracking**: Track blocking relationships (`tk dep`, `tk dep tree`, `tk blocked`, `tk ready`, `tk dep cycle`).
- **In-Place Ticket Updates**: Update fields, design notes, and acceptance criteria on the fly with `tk update`.
- **Extensible Plugin System**: Discovers `tk-<cmd>` or `ticket-<cmd>` executables in `$PATH` automatically.
- **Fast Bulk Operations**: Powered by portable `awk` and `sed` routines.

### 🌐 Interactive Web UI (`tk webui` / `tk-webui`)
- **4-Lane Kanban Board**: Fluid drag-and-drop between Ready, In Progress, Blocked, and Closed lanes.
- **Multi-View Switcher**: Toggle instantly between **Kanban**, **Table View**, **Interactive Dependency Tree Graph**, and **Timeline/Gantt View**.
- **In-Place Task Editing**: Edit title, description, tags, priority, assignee, design notes, and acceptance criteria directly in the browser.
- **PR-Style Review Feedback**: Chronological audit trail for review notes and comments (`Cmd+Enter` to submit).
- **Collapsible Completed Tasks**: Automatically cleans up closed tasks with a 1-click toggle to view older tasks.
- **Multi-Project Switcher**: Switch between any repositories containing `.tickets/` on your system.

---

## 📖 CLI Usage

```bash
tk - minimal ticket system with dependency tracking

Usage: tk <command> [args]

Commands:
  create [title] [options] Create ticket, prints ID
    -d, --description      Description text
    --design               Design notes
    --acceptance           Acceptance criteria
    -t, --type             Type (bug|feature|task|epic|chore) [default: task]
    -p, --priority         Priority 0-4, 0=highest [default: 2]
    -a, --assignee         Assignee
    --external-ref         External reference (e.g., gh-123, JIRA-456)
    --parent               Parent ticket ID
    --tags                 Comma-separated tags (e.g., --tags ui,backend,urgent)
  start <id>               Set status to in_progress
  close <id>               Set status to closed
  reopen <id>              Set status to open
  status <id> <status>     Update status (open|in_progress|closed)
  update <id> [options]    Update title, description, priority, tags, etc.
  dep <id> <dep-id>        Add dependency (id depends on dep-id)
  dep tree [--full] <id>   Show dependency tree (--full disables dedup)
  dep cycle                Find dependency cycles in open tickets
  undep <id> <dep-id>      Remove dependency
  link <id> <id> [id...]   Link tickets together (symmetric)
  unlink <id> <target-id>  Remove link between tickets
  ready [-a X] [-T X]      List open/in-progress tickets with deps resolved
  blocked [-a X] [-T X]    List open/in-progress tickets with unresolved deps
  closed [--limit=N] [-a X] [-T X] List recently closed tickets (default 20, by mtime)
  show <id>                Display ticket
  add-note <id> [text]     Append timestamped note (or pipe via stdin)
  super <cmd> [args]       Bypass plugins, run built-in command directly

Plugins (tk-<cmd> or ticket-<cmd> in PATH):
  webui                  Interactive Kanban Web UI & PR review dashboard
```

---

## 🔌 Writing Plugins

Plugins are executables named `tk-<cmd>` or `ticket-<cmd>` in `$PATH`.

Add metadata comments in the first 10 lines of your script:
```bash
#!/usr/bin/env bash
# tk-plugin: description for tk help
# tk-plugin-version: 1.0.0

set -euo pipefail
# implementation here
```

Or for compiled binaries, implement the `--tk-describe` flag:
```bash
$ my-binary --tk-describe
tk-plugin: description for tk help
```

---

## 📚 Documentation & Specifications

- **[System & Data Specification (SPEC.md)](docs/SPEC.md)**: Complete schema, DAG semantics, error codes, and lifecycle specification (spec-driven architecture).
- **[Plugin Architecture Guide (PLUGINS.md)](docs/PLUGINS.md)**: Guide on writing and distributing custom plugins with metadata discovery and version contracts.
- **[AI Agent Integration Guide (AGENTS.md)](docs/AGENTS.md)**: Operational patterns, subtask decomposition workflows, and ready-queue traversal for AI coding agents.
- **[Agent Skill (SKILL.md)](skills/tk/SKILL.md)**: Agent skill definition installable to `~/.agents/skills/tk/SKILL.md`.

---

## 🧪 Testing

The test suite is written using [Behave](https://behave.readthedocs.io/en/latest/).

```bash
make test
```

---

## 🙏 Credits & Acknowledgments

This project is built upon the foundational architecture and minimal design created by [**wedow**](https://github.com/wedow) in the original [`wedow/ticket`](https://github.com/wedow/ticket) project. We extend deep gratitude to the original author and contributors for creating such an elegant, git-backed ticket tracking foundation for developers and AI agents.

---

## 📝 License

[MIT License](LICENSE)
