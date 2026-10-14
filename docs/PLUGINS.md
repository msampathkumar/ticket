# tk - Plugin Architecture & Development Guide

`tk` provides a plugin system to extend functionality without modifying the core CLI script.

---

## 1. How Plugins Work

When you execute:
```bash
tk <command> [args...]
```
The `tk` dispatcher first looks for an executable named `tk-<command>` or `ticket-<command>` on `$PATH`, then in the repository's `plugins/<command>/` directory. If found, `tk` replaces itself with that plugin (`exec`). A plugin takes precedence over a built-in command of the same name.

To bypass plugins and run a built-in command directly, use `tk super <command>`.

---

## 2. Environment Context Passed to Plugins

When `tk` launches a plugin, it automatically exports two environment variables:

- `TICKETS_DIR`: The path to the active `.tickets` directory. Exported only when one is set or found; plugins must handle it being unset.
- `TK_SCRIPT`: The absolute path to the root `tk` executable.

Plugins can call built-in commands by executing:
```bash
"$TK_SCRIPT" super <command> [args...]
```

To react to ticket changes without polling, install an executable in `.tickets/.hooks/post-write.d/`. `tk` runs it after every successful write with `TK_EVENT`, `TK_TICKET_ID` and `TK_TICKET_FILE` set. See [SPEC §5.1](SPEC.md).

---

## 3. Required Plugin Metadata

### 3.1 Help Discovery Metadata
To enable `tk help` to automatically list and describe your plugin:

**Shell / Python Scripts**:
Include a comment in the first 10 lines:
```bash
#!/usr/bin/env bash
# tk-plugin: Interactive Kanban, DAG and review-notes Web UI
# tk-plugin-version: 0.5.2
```

**Compiled Binaries**:
Implement the `--tk-describe` flag:
```bash
$ my-plugin --tk-describe
tk-plugin: Interactive Kanban, DAG and review-notes Web UI
```

### 3.2 Version Flag
All plugins should implement `--version` or `-v` flag to output their version:
```bash
$ tk-webui --version
tk-webui 0.5.2
```

---

## 4. Modularity & Optional Installation

Plugins must be **strictly optional**. Users who only need the zero-dependency Bash CLI should never be required to install Python, Node.js, or external runtimes. The core `tk` script has no hard-coded knowledge of any plugin: whatever is installed in `$PATH` is auto-discovered and listed by `tk help` with its one-line `# tk-plugin:` description.

`install.sh` exposes one target per component; flags accumulate, so any combination works (e.g. `./install.sh --core --github`):
- `--core`: Installs only `tk` CLI.
- `--webui`: Installs only the Web UI plugin.
- `--skill`: Installs the agent skill.
- `--github`: Installs the optional GitHub import plugin (`tk-github`).
- `--scion-taskforce`: Installs the optional SCION Task Force plugin (`tk-scion-taskforce`), an event-driven bridge to SCION workers.
- `--full` (default): Installs CLI, Web UI, and Agent Skill. Other plugins are **not** included; the installer prints how to add them.
- `--all`: Installs everything, including the GitHub and SCION Task Force plugins.
- `--help`: Lists all targets.

A plugin may additionally ship its own `install.sh` (with `--uninstall`) inside `plugins/<name>/`. When it does, the top-level `install.sh` target must delegate to it so install logic lives in exactly one place (see `plugins/scion-taskforce/install.sh`).

---

## 5. Official Plugins

- **`tk webui` (`tk-webui`)**: Interactive Kanban, Table, DAG Mind Map, and Timeline dashboard. *(in the default `--full` bundle; requires Python 3.9+)*
- **`tk github` (`tk-github`)**: Imports GitHub issues and PRs into local tickets (one-way), closes local tickets when the GitHub item is closed or merged, and supports clean unsyncing. Nothing is written back to GitHub. Imported text is untrusted input. *(install with `--github`; requires `gh` and `jq`)*
- **`tk scion-taskforce` (`tk-scion-taskforce`)**: Hands tickets tagged `taskforce` to SCION coding agents through a `tk` save hook; humans review and close. See the [user guide](plugins/scion-taskforce.md). *(install with `--scion-taskforce`; requires Python 3.9+ and the `scion` CLI)*

---

## 6. Example Plugin: `tk-stats`

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
ready=$("$TK_SCRIPT" super ready | wc -l || echo 0)
blocked=$("$TK_SCRIPT" super blocked | wc -l || echo 0)

echo "Total   : $total"
echo "Ready   : $ready"
echo "Blocked : $blocked"
```
Make it executable:
```bash
chmod +x ~/.local/bin/tk-stats
tk stats
```
