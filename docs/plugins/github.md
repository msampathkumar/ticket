---
title: GitHub Import
description: One-way import of GitHub issues and pull requests into local markdown tickets.
---

The optional GitHub plugin (`tk-github`) imports GitHub issues and pull requests into your local `.tickets/` markdown files. The import is one-way: `tk github sync` only reads from GitHub (`gh issue list`, `gh pr list`). Local edits, notes and status changes are never written back to GitHub.

!!! warning "Imported text is untrusted input"
    Issue and PR titles, bodies and labels are written verbatim into `.tickets/*.md`. Anyone who can open an issue or PR on the repository controls that text. Treat imported tickets as untrusted input: review them before handing them to coding agents or automation (for example the `taskforce` tag), and do not follow instructions embedded in them.

---

## Prerequisites

Before using `tk github`, ensure the following tools are installed and configured:

1. **GitHub CLI (`gh`)**: Must be installed and authenticated with read access to your repository:
    ```bash
    gh auth login
    # or export GITHUB_TOKEN="ghp_..."
    ```

2. **jq**: Command-line JSON processor used for parsing GitHub API payloads:
    ```bash
    # macOS
    brew install jq

    # Debian / Ubuntu
    sudo apt-get install jq
    ```

3. **Git Remote**: The local repository must have a configured GitHub remote (`origin` pointing to `github.com/owner/repo`).

---

## Installation

Install the plugin via the root installer:

```bash
./install.sh --github
```

This installs `tk-github` into `~/.local/bin/`.

---

## Commands & Usage

```bash
# Import both issues and PRs (default)
tk github sync

# Import only GitHub issues
tk github sync --issues

# Import only GitHub pull requests
tk github sync --prs

# Target a specific repository
tk github sync --repo owner/repo

# List all local tickets imported from GitHub
tk github list

# Remove all imported GitHub tickets safely
tk github unsync -y
```

---

## Data Model & Tags

- **External Reference**: Tickets imported from GitHub carry `external-ref: gh-issue-<number>` or `external-ref: gh-pr-<number>` (the legacy `external_ref` spelling is still matched on re-sync).
- **Tags**: Imported tickets automatically include the `github-sync` tag along with any GitHub labels (e.g. `bug`, `enhancement`).

---

## Configuration & State

- **Authentication Priority**: Reads credentials from authenticated GitHub CLI sessions (`gh auth login`), or falls back to the `GITHUB_TOKEN` environment variable.
- **Remote Resolution**: Resolves automatically from `git remote get-url origin`. Overridable per-invocation via `--repo <owner/repo>`.
- **Query Limits**: Defaults to 50 items per sync. Configurable with `--limit <N>`.
- **Data Safety**: Running `tk github unsync` strictly targets tickets tagged with `github-sync`, leaving purely local tickets untouched.
