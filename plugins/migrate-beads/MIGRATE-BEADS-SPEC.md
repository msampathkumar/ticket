# Beads Migration Plugin Specification (MIGRATE-BEADS-SPEC.md)

- **Plugin Name**: `tk-migrate-beads` / `ticket-migrate-beads`
- **Command**: `tk migrate-beads`
- **Version**: `1.0.0`
- **Installation**: Optional

---

## 1. Overview

`tk-migrate-beads` migrates legacy `beads` issue repositories (`.beads/` JSON files) into standard `tk` Markdown format in `.tickets/`.

---

## 2. CLI Interface

```bash
tk migrate-beads [source-dir]
```

### Behavior
- Reads `.beads/*.json` or bead issues from the source directory.
- Converts each bead issue into a corresponding YAML frontmatter Markdown file in `.tickets/`.
- Preserves titles, descriptions, dependency relationships, and state transitions.
