# List Plugin Specification (LS-SPEC.md)

- **Plugin Name**: `tk-ls` / `ticket-ls` / `ticket-list`
- **Command**: `tk ls` / `tk list`
- **Version**: `1.0.0`
- **Installation**: Optional (`./install.sh --all` or symlink)

---

## 1. Overview

`tk-ls` provides formatted, filterable listings of tickets directly on the command line using fast, native `awk` processing over `.tickets/*.md`.

---

## 2. CLI Interface & Flags

```bash
tk ls [options]
```

### Options
- `--status=<open|in_progress|closed>`: Filter tickets by status.
- `-a, --assignee=<name>`: Filter tickets by assignee.
- `-T, --tag=<tag>`: Filter tickets by tag.
- `--version` / `-v`: Displays plugin version (`1.0.0`).
- `--help` / `-h`: Displays plugin usage.

---

## 3. Output Format

```
<id> [<status>] - <title> [<- <dependency-ids>]
```

Example:
```
tic-6mex [open] - feat: Add setting
tic-d04l [open] - feat: Update Tree Graph <- [tic-6mex]
```

---

## 4. Dependencies

- `awk` (standard POSIX)
