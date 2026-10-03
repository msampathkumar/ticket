---
title: Plugin Architecture
description: Extend ticket CLI with custom plugins in Bash or Python.
---

`ticket` features a lightweight, zero-overhead plugin architecture based on executable discovery.

---

### How Plugins Work

When you execute:
```bash
tk <command> [args...]
```
The `tk` dispatcher looks for an executable named `tk-<command>` or `ticket-<command>` in your system `$PATH`. If found, execution is delegated directly to that binary or script.

To bypass plugins and run a built-in command directly, use `tk super <command>`.

---

### Environment Context Passed to Plugins

When `tk` launches a plugin, it exports two environment variables:
- `TICKETS_DIR`: Absolute path to active `.tickets` directory.
- `TK_SCRIPT`: Absolute path to root `tk` executable (`"$TK_SCRIPT" super ...`).

---

### Example Plugin (`tk-stats`)

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
open=$("$TK_SCRIPT" super ready | wc -l || echo 0)
echo "🟢 Ready Tasks: $open"
```
Place in `~/.local/bin/tk-stats` and run `tk stats`.
