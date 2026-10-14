# <img src="docs/images/logo.svg" width="30" height="30" alt="tk logo" style="vertical-align: -4px; display: inline-block;" /> ticket (tk)

[![Test Suite](https://img.shields.io/github/actions/workflow/status/msampathkumar/ticket/test.yml?branch=master&label=tests&style=flat-square)](https://github.com/msampathkumar/ticket/actions/workflows/test.yml)
[![Documentation](https://img.shields.io/badge/docs-website-indigo.svg?style=flat-square)](https://msampathkumar.github.io/ticket/)
[![Release](https://img.shields.io/github/v/release/msampathkumar/ticket?style=flat-square&color=6366f1)](https://github.com/msampathkumar/ticket/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Linux-lightgrey.svg?style=flat-square)](#)
[![Zero Dependency Core](https://img.shields.io/badge/core-portable%20Bash%20(no%20Python)-10b981.svg?style=flat-square)](docs/SPEC.md#non-goals)

Minimal, dependency-aware task tracker. Built to scale agentic workflows.

- **Documentation**: [https://msampathkumar.github.io/ticket/](https://msampathkumar.github.io/ticket/)
- **LLM Context**: [`llms.txt`](https://msampathkumar.github.io/ticket/llms.txt) | [`llms-full.txt`](https://msampathkumar.github.io/ticket/llms-full.txt)

---

## Terminal Demo

![ticket CLI Demo](docs/images/demo.gif)

---

## Quick Install

Install the core Bash CLI (no Python or Node) or the full suite with the interactive Web UI:

```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Full Suite (CLI + Web UI + Agent Skill) — default
./install.sh --full

# Core CLI Only (Pure Bash, zero Python dependencies)
./install.sh --core
```

Binaries install to `~/.local/bin/` (`tk`, `tk-webui`, plus any optional `tk-<plugin>`). Ensure `~/.local/bin` is in `$PATH`.

### Install Agent Skill via NPX

Install the agent skill for your AI coding assistant without cloning:

```bash
npx github:msampathkumar/ticket agent-skill --install
```

---

## Architecture & Concepts

- **Plain Text State**: State resides in `.tickets/*.md` files with YAML frontmatter, versioned directly in Git alongside your code. IDs look like `tic-a1b2c3` (prefix plus a 6-char hash); older 4-char IDs and unique partial IDs still resolve.
- **DAG Dependency Intelligence**: Track blocking relationships (`tk dep`), blockers (`tk blocked`), and unblocked work ready to execute (`tk ready`).
- **Deterministic Agent Loop**: 5-step loop (`tk ready` -> `tk start <id> --claim` -> `tk show` -> `tk add-note` -> `tk close`). `--claim` is atomic: when several agents race for one ticket, exactly one wins and the others exit `3`.
- **Portable Bash Core**: The root `ticket` executable is a single portable Bash script (Bash 3.2+, macOS and Linux) using `awk`, `sed`, and other standard tools. No Python or Node; `jq` is optional, only for `tk query <filter>`.
- **Minimal Scope**: Core is the shared task queue. Orchestration, sync, and UI live in optional plugins. See [Scope and Non-goals](docs/SPEC.md#non-goals).

For complete CLI command references, guides, and visual workflows, see the **[Documentation Website](https://msampathkumar.github.io/ticket/)**.

---

## Official Plugins

Extend `ticket` with modular plugins discovered automatically via `$PATH`:

- **[Web UI (`tk webui`)](https://msampathkumar.github.io/ticket/plugins/webui/)**: Interactive 4-lane Kanban board, DAG Mind Map graph, table view, and background daemon manager (`tk webui server start`). Local-only by default: it binds `127.0.0.1` with no authentication, and rejects foreign Host headers and cross-origin writes. Anyone who can reach the port can edit tickets, so do not bind it to a shared network.
- **[GitHub Import (`tk github`)](https://msampathkumar.github.io/ticket/plugins/github/)**: One-way import of GitHub issues and pull requests into local markdown tickets. Nothing is written back to GitHub.
- **[SCION Task Force (`tk scion-taskforce`)](https://msampathkumar.github.io/ticket/plugins/scion-taskforce/)**: Event-driven bridge from tickets to SCION coding agents: saving a `taskforce` ticket starts its SCION worker; humans review and close.

To author your own plugin, see the **[Plugin Architecture Guide](https://msampathkumar.github.io/ticket/plugins/architecture/)**.

---

## Contributor & Developer Guide

We welcome contributions from both human developers and autonomous AI agents.

### Development Prerequisites
- **Bash 3.2+** and standard Unix tools (`awk`, `sed`, `grep`, `find`)
- **Python 3.9+** and **`uv`** (for the BDD tests, Web UI, plugins, and documentation server; CI runs Python 3.11 and 3.13)
- **`shellcheck`** (Bash lint, run in CI at `-S warning`)
- Optional: **`jq`** (for `tk query <filter>`), **`gh`** (for the GitHub plugin)

### Running the Test Suite
The acceptance test suite uses [Behave](https://behave.readthedocs.io/en/latest/):

```bash
make test
shellcheck -S warning ticket            # Bash lint (CI)
uvx ruff check tk_webui/ plugins/scion-taskforce/   # Python lint (CI)
```

### Local Documentation Server
The documentation portal is built with Zensical:

```bash
make docs-dev    # Start local live-reload documentation server (http://localhost:8000/ticket/)
make docs-build  # Build production static bundle and refresh LLM files
```

### Contributing Principles
1. **Preserve Zero-Dependency Core**: The core `ticket` executable must remain a single portable Bash script (not POSIX `sh`) that passes `shellcheck -S warning`, with no runtime beyond Bash and standard Unix tools. Respect the [Non-goals](docs/SPEC.md#non-goals).
2. **BDD Verification**: All new CLI commands or behavior modifications must be accompanied by Behave acceptance scenarios in `features/`.
3. **Specification-Driven**: Review [`docs/SPEC.md`](docs/SPEC.md) for data model schemas, exit codes, and lifecycle specifications before proposing major architectural changes.
4. **Agent-Friendly**: Keep documentation and command outputs parseable, clean, and documented in `llms.txt`.

---

## Credits & Acknowledgments

- Built upon the foundational architecture and minimal design created by [**wedow**](https://github.com/wedow) in the original [`wedow/ticket`](https://github.com/wedow/ticket) project.
- Inspired by Joe Armstrong's concept of the [Minimal Viable Program](https://joearms.github.io/published/2014-06-25-minimal-viable-program.html).

---

## License

[MIT License](LICENSE)
