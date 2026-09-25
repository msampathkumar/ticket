# Ticket Plugins

Official plugins that extend `tk` with additional commands.

All plugins follow the official [Plugin Specification Standard (PLUGIN_SPEC.md)](../docs/PLUGIN_SPEC.md). Except for the Web UI, all plugins are strictly optional to install.

---

## 📁 Plugin Directories & Specifications

| Plugin Folder | Command | Spec Document | Description |
| :--- | :--- | :--- | :--- |
| [`webui/`](../tk_webui) | `tk webui` | [WEBUI-SPEC.md](../tk_webui/WEBUI-SPEC.md) | Full-featured Kanban, Table, Mind Map DAG, and Timeline dashboard |
| [`github/`](github/) | `tk github` | [GITHUB-SPEC.md](github/GITHUB-SPEC.md) | Sync GitHub issues & pull requests into local tickets |
| [`ls/`](ls/) | `tk ls` / `tk list` | [LS-SPEC.md](ls/LS-SPEC.md) | Formatted ticket listings with status, assignee, and tag filters |
| [`edit/`](edit/) | `tk edit` | [EDIT-SPEC.md](edit/EDIT-SPEC.md) | Open ticket in `$EDITOR` / `$VISUAL` |
| [`query/`](query/) | `tk query` | [QUERY-SPEC.md](query/QUERY-SPEC.md) | Structured JSON queries and programmatic data access |
| [`migrate-beads/`](migrate-beads/) | `tk migrate-beads` | [MIGRATE-BEADS-SPEC.md](migrate-beads/MIGRATE-BEADS-SPEC.md) | Migration from legacy beads issue repositories |

---

## 🔌 Writing Plugins

Each plugin lives in its own folder under `plugins/<plugin-name>/` and includes:
1. An executable named `ticket-<name>` and a symlink `tk-<name>`
2. A specification file named `<PLUGIN-NAME>-SPEC.md`
3. Metadata comments in the first 10 lines:

```bash
#!/usr/bin/env bash
# tk-plugin: description for tk help
# tk-plugin-version: 1.0.0

set -euo pipefail
```

Or for compiled binaries, implement `--tk-describe` and `--version`.

---

## 🌐 Environment Variables

Plugins receive:
- `TICKETS_DIR` — absolute path to `.tickets/` directory
- `TK_SCRIPT` — absolute path to the `tk` executable

Use `"$TK_SCRIPT" super <cmd>` to call built-ins without recursing into plugins.
