# tk - Plugin Architecture & Development Guide

`tk` features an extensible, lightweight plugin system that allows extending functionality without modifying the core CLI script.

---

## 1. How Plugins Work

When you execute:
```bash
tk <command> [args...]
```
The `tk` dispatcher first checks for an executable named `tk-<command>` or `ticket-<command>` in your system `$PATH`. If found, `tk` delegates execution directly to that plugin binary or script.

To bypass plugins and run a built-in command directly, use `tk super <command>`.

---

## 2. Environment Context Passed to Plugins

When `tk` launches a plugin, it automatically exports two environment variables:

- `TICKETS_DIR`: The absolute path to the active `.tickets` directory.
- `TK_SCRIPT`: The absolute path to the root `tk` executable.

Plugins can call built-in commands by executing:
```bash
"$TK_SCRIPT" super <command> [args...]
```

---

## 3. Required Plugin Metadata

### 3.1 Help Discovery Metadata
To enable `tk help` to automatically list and describe your plugin:

**Shell / Python Scripts**:
Include a comment in the first 10 lines:
```bash
#!/usr/bin/env bash
# tk-plugin: Interactive Kanban Web UI & PR review dashboard
# tk-plugin-version: 0.2.0
```

**Compiled Binaries**:
Implement the `--tk-describe` flag:
```bash
$ my-plugin --tk-describe
tk-plugin: Interactive Kanban Web UI & PR review dashboard
```

### 3.2 Version Flag
All plugins should implement `--version` or `-v` flag to output their version:
```bash
$ tk-webui --version
tk-webui 0.2.0
```

---

## 4. Modularity & Optional Installation

Plugins must be **strictly optional**. Users who only need the zero-dependency Bash CLI should never be required to install Python, Node.js, or external runtimes.

In `install.sh`, provide modular targets:
- `--core`: Installs only `tk` CLI.
- `--webui`: Installs only the Web UI plugin.
- `--skill`: Installs the agent skill.
- `--github`: Installs the optional GitHub sync plugin (`tk-github`).
- `--full`: Installs CLI, Web UI, and Agent Skill.
- `--all`: Installs all plugins and skills.

---

## 5. Official Plugins

- **`tk webui` (`tk-webui`)**: Full-featured interactive Kanban, Table, DAG Mind Map, and Timeline review dashboard.
- **`tk github` (`tk-github`)**: Syncs GitHub issues and PRs with local tickets, updates statuses on close/merge, and supports clean unsyncing.

---

## 5. Example Plugin: `tk-stats`

Here is a minimal plugin example (`~/.local/bin/tk-stats`):

```bash
#!/usr/bin/env bash
# tk-plugin: Quick summary of open and closed ticket statistics
# tk-plugin-version: 1.0.0
set -euo pipefail

if [[ "${1:-}" == "--version" || "${1:-}" == "-v" ]]; then
    echo "tk-stats 1.0.0"
    exit 0
fi

if [[ "${1:-}" == "--tk-describe" ]]; then
    echo "tk-plugin: Quick summary of open and closed ticket statistics"
    exit 0
fi

TICKETS_DIR="${TICKETS_DIR:-.tickets}"

total=$(ls -1 "$TICKETS_DIR"/*.md 2>/dev/null | wc -l || echo 0)
open=$("$TK_SCRIPT" super ready | wc -l || echo 0)
blocked=$("$TK_SCRIPT" super blocked | wc -l || echo 0)

echo "📊 Total Tickets : $total"
echo "🟢 Ready (Open)  : $open"
echo "🔴 Blocked       : $blocked"
```
Make it executable:
```bash
chmod +x ~/.local/bin/tk-stats
tk stats
```
