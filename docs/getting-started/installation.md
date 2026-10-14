---
title: Installation
description: How to install ticket (tk) and its modular plugins.
---

`ticket` (`tk`) has a single-file Bash core with no runtime dependencies. Plugins are optional; install only what you need.

## Quick Install

Clone the repository and run the modular installer:

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Full Suite (CLI + Web UI + Agent Skill) — default
./install.sh --full
```

Binaries are installed to `~/.local/bin/` (override with `BIN_DIR`). Ensure that directory is on your `$PATH`.

---

## Requirements

**Core CLI**: Bash 3.2+ and standard Unix tools (`awk`, `sed`, `grep`, `find`, `mkdir`, `date`) on macOS or Linux. Python and Node are not used.

| Optional tool | Used for |
| :--- | :--- |
| `jq` | `tk query <filter>` (unfiltered `tk query` works without it) |
| `rg` (ripgrep) | Faster `tk find`; `grep` is used otherwise |
| `git` | Sharing tickets; default assignee from `git config user.name` |

---

## Installation Flags

Flags accumulate, so any combination works (e.g. `./install.sh --core --github`):

| Flag | Installs | Requires |
| :--- | :--- | :--- |
| `--core`, `-c` | Core `tk` CLI | Bash 3.2+ |
| `--webui`, `-w` | Web UI plugin (`tk webui`) in a local `.venv` | Python 3.9+ with `uv` or `pip` |
| `--skill`, `-s` | Agent skill to `~/.agents/skills/tk/SKILL.md` | None |
| `--github`, `-g` | GitHub import plugin (`tk github`) | `gh` (authenticated), `jq` |
| `--scion-taskforce`, `-t` | SCION Task Force plugin (`tk scion-taskforce`) | Python 3.9+, `scion` CLI |
| `--full`, `-f` | **(Default)** Core, Web UI and Agent Skill | Python 3.9+ (for the Web UI) |
| `--all` | Everything above | All of the above |

### Examples

```bash
# Core CLI only (no Python required)
./install.sh --core

# Core CLI + GitHub import plugin
./install.sh --core --github

# Everything, including the GitHub and SCION Task Force plugins
./install.sh --all
```
