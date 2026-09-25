# Edit Plugin Specification (EDIT-SPEC.md)

- **Plugin Name**: `tk-edit` / `ticket-edit`
- **Command**: `tk edit`
- **Version**: `1.0.0`
- **Installation**: Optional (`./install.sh --all` or symlink)

---

## 1. Overview

`tk-edit` opens a ticket's underlying Markdown file in the user's preferred `$EDITOR` or `$VISUAL` (falling back to `nano` or `vi`).

---

## 2. CLI Interface

```bash
tk edit <ticket-id>
```

### Environment Variables
- `EDITOR`: Preferred terminal editor (e.g. `vim`, `nano`, `code`).
- `VISUAL`: Preferred visual editor.
- `TICKETS_DIR`: Resolved `.tickets/` path.

---

## 3. Behavior & Error Handling

- Resolves partial IDs (e.g., `tk edit 6me` opens `tic-6mex.md`).
- Errors if ticket ID does not match any file in `.tickets/`.
