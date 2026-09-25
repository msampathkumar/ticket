# Query Plugin Specification (QUERY-SPEC.md)

- **Plugin Name**: `tk-query` / `ticket-query`
- **Command**: `tk query`
- **Version**: `1.0.0`
- **Installation**: Optional (`./install.sh --all` or symlink)

---

## 1. Overview

`tk-query` provides structured JSON queries over ticket frontmatter and content for shell scripts, jq pipelines, and automation tools.

---

## 2. CLI Interface

```bash
tk query [options]
```

### Options
- `--json`: Output full ticket objects as a JSON array.
- `--filter=<field=val>`: Filter tickets matching key-value frontmatter pairs.
- `--ids-only`: Output only space/newline-separated ticket IDs.

---

## 3. Dependencies

- `awk`, `sed`
- `jq` (optional for advanced JSON filtering)
