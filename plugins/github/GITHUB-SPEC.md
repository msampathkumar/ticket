# GitHub Sync Plugin Specification (GITHUB-SPEC.md)

- **Plugin Name**: `tk-github` / `ticket-github`
- **Command**: `tk github`
- **Version**: `0.1.0`
- **Installation**: Optional (`./install.sh --github`)

---

## 1. Overview

`tk-github` provides bidirectional-aware synchronization between GitHub issues/pull requests and local `.tickets/` markdown files. It enables tracking remote GitHub work as local tickets with automated state reconciliation and clean removal.

---

## 2. CLI Interface & Commands

```bash
tk github <command> [options]
```

### Commands
- `sync` *(default)*: Fetches open GitHub issues and pull requests, creating local tickets or updating statuses of closed items.
- `unsync`: Removes all tickets tagged with `github-sync`. Supports `--force` / `-y`.
- `list` | `status`: Displays a tabular overview of all GitHub-synced local tickets.
- `version` | `--version` | `-v`: Displays plugin version (`tk-github 0.1.0`).
- `help` | `--help` | `-h`: Displays plugin help.

### Options
- `--issues`: Sync only GitHub issues.
- `--prs`: Sync only GitHub pull requests.
- `--all`: Sync both issues and PRs (default).
- `--repo <owner/repo>`: Target a specific remote GitHub repository instead of the current working repository.
- `--limit <N>`: Maximum items to query (default: 50).
- `--force`, `-y`: Skip confirmation when unsyncing.

---

## 3. Data Model & Tags

- **External Reference**:
  - Issues: `external_ref: gh-issue-<number>`
  - Pull Requests: `external_ref: gh-pr-<number>`
- **Tags**:
  - `github-sync` (always attached to synced tickets)
  - `issue` or `pr`
  - GitHub labels (e.g. `bug`, `enhancement`, `documentation`)
- **Body Content**:
  - Markdown body contains the issue/PR description and a direct link: `**GitHub URL:** <url>`.

---

## 4. Dependencies

- `gh` (GitHub CLI, authenticated via `gh auth login`)
- `jq` (JSON processor)
