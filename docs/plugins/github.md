---
title: GitHub Sync
description: Bi-directional synchronization between local markdown tickets and GitHub issues and pull requests.
---

The optional GitHub plugin (`tk-github`) enables bi-directional synchronization between your local `.tickets/` markdown files and GitHub issues and pull requests.

---

## Prerequisites

Before using `tk github`, ensure the following tools are installed and configured:

### 1. GitHub CLI (`gh`)
Must be installed and authenticated with read/write access to your repository:

```bash
gh auth login
# or export GITHUB_TOKEN="ghp_..."
```

### 2. jq
Command-line JSON processor used for parsing GitHub API payloads:

```bash
# macOS
brew install jq

# Debian / Ubuntu
sudo apt-get install jq
```

### 3. Git Remote
The local repository must have a configured GitHub remote (`origin` pointing to `github.com/owner/repo`).

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
# Sync both issues and PRs (default)
tk github sync

# Sync only GitHub issues
tk github sync --issues

# Sync only GitHub pull requests
tk github sync --prs

# Target a specific repository
tk github sync --repo owner/repo

# List all local tickets synced from GitHub
tk github list

# Remove all synced GitHub tickets safely
tk github unsync -y
```

---

## Data Model & Tags

- **External Reference**: Tickets synced from GitHub carry `external_ref: gh-issue-<number>` or `external_ref: gh-pr-<number>`.
- **Tags**: Synced tickets automatically include the `github-sync` tag along with any GitHub labels (e.g. `bug`, `enhancement`).

---

## Configuration & State

- **Authentication Priority**: Reads credentials from authenticated GitHub CLI sessions (`gh auth login`), or falls back to the `GITHUB_TOKEN` environment variable.
- **Remote Resolution**: Resolves automatically from `git remote get-url origin`. Overridable per-invocation via `--repo <owner/repo>`.
- **Query Limits**: Defaults to 50 items per sync. Configurable with `--limit <N>`.
- **Data Safety**: Running `tk github unsync` strictly targets tickets tagged with `github-sync`, leaving purely local tickets untouched.
