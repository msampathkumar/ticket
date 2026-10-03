---
title: Installation
description: How to install ticket (tk) and its modular plugins.
---

`ticket` (`tk`) is designed with a **zero-dependency POSIX Bash core** and **modular optional plugins**. You can install only what you need.

## ⚡ Quick Install

Clone the repository and run the modular installer:

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Full Suite (CLI + Web UI + Agent Skill) — default
./install.sh --full
```

Binaries are installed to `~/.local/bin/` (`tk`, `tk-webui`, plus optional plugin binaries). Ensure `~/.local/bin` is in your `$PATH`.

---

## 🧩 Modular Installation Flags

The installer supports composable flags so you can install precisely the components you require:

| Flag | Description | Mandatory Dependencies |
| :--- | :--- | :--- |
| `--core` | Installs only the core `tk` POSIX Bash CLI | **Zero** (Pure Bash) |
| `--webui` | Installs the interactive Kanban & DAG Web UI (`tk-webui`) | Python 3.9+, FastAPI |
| `--skill` | Installs the AI agent skill (`tk-agent-skill`) | None |
| `--github` | Installs the optional GitHub sync plugin (`tk-github`) | Python / Bash |
| `--scion-taskforce` | Installs the autonomous SCION Task Force worker orchestrator (`tk-scion-taskforce`) | Python 3.9+, `scion` CLI |
| `--full` | **(Default)** Installs Core CLI, Web UI, and Agent Skill | Python 3.9+ (for Web UI) |
| `--all` | Installs everything, including optional plugins | Python 3.9+, `scion` CLI |

### Examples

```bash
# Install only the lightweight core CLI (no Python/Node required)
./install.sh --core

# Install Core CLI + GitHub sync plugin
./install.sh --core --github

# Install everything including optional plugins
./install.sh --all
```
