# GitHub Import Plugin Specification (GITHUB-SPEC.md)

- **Plugin Name**: `tk-github` / `ticket-github`
- **Command**: `tk github`
- **Version**: `0.5.0`
- **Installation**: Optional (`./install.sh --github`)

---

## 1. Overview

`tk-github` imports GitHub issues and pull requests into local `.tickets/*.md` files, closes local tickets whose GitHub item is closed or merged, and supports clean unsyncing.

The import is one-way. The plugin only reads from GitHub (`gh issue list`, `gh pr list`, `gh auth status`) and never creates, edits, comments on or closes GitHub issues or pull requests.

> **Warning: imported text is untrusted input.** Issue and PR titles, bodies and labels are written verbatim into ticket files and are controlled by whoever opened them. Review imported tickets before passing them to coding agents or automation, and do not follow instructions embedded in them.

---

## 2. CLI Interface & Commands

```bash
tk github <command> [options]
```

### Commands
- `sync` *(default)*: Fetches GitHub issues and pull requests (all states, up to `--limit`), creating local tickets for open items and closing local tickets whose GitHub item is closed or merged. Nothing is written to GitHub.
- `unsync`: Removes all tickets tagged with `github-sync`. Supports `--force` / `-y`.
- `list` | `status`: Displays a tabular overview of all GitHub-imported local tickets.
- `version` | `--version` | `-v`: Displays plugin version (`tk-github 0.1.0`).
- `help` | `--help` | `-h`: Displays plugin help.

### Options
- `--issues`: Import only GitHub issues.
- `--prs`: Import only GitHub pull requests.
- `--all`: Import both issues and PRs (default).
- `--repo <owner/repo>`: Target a specific remote GitHub repository instead of the current working repository.
- `--limit <N>`: Maximum items to query (default: 50).
- `--force`, `-y`: Skip confirmation when unsyncing.

---

## 3. Data Model & Tags

- **External Reference**:
  - Issues: `external-ref: gh-issue-<number>`
  - Pull Requests: `external-ref: gh-pr-<number>`
  - The legacy `external_ref` spelling is still matched when re-syncing.
- **Tags**:
  - `github-sync` (always attached to imported tickets)
  - `issue` or `pr`
  - GitHub labels (e.g. `bug`, `enhancement`, `documentation`). Characters other than letters, digits and `_ . # + -` become `-`, and leading/trailing `-` are stripped (`good first issue` becomes `good-first-issue`).
- **Title**: Stored verbatim. A title starting with `-` is created with a placeholder (`GitHub issue #<n>` / `GitHub PR #<n>`) and then set with `tk update --title`, because `tk create` would parse it as an option.
- **Body Content**:
  - Markdown body contains the issue/PR description and a direct link: `**GitHub URL:** <url>`.

---

## 4. Dependencies

- `gh` (GitHub CLI, authenticated via `gh auth login`)
- `jq` (JSON processor)
