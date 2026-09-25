# Web UI Plugin Specification (WEBUI-SPEC.md)

- **Plugin Name**: `tk-webui`
- **Command**: `tk webui`
- **Version**: `0.2.0`
- **Installation**: Included in Full Installation (`./install.sh --full` or `./install.sh --webui`)

---

## 1. Overview

`tk-webui` is the official modern web application and review dashboard for `tk`. It runs a local FastAPI web server serving a vanilla HTML5/JavaScript application with Tailwind CSS and Marked.js.

---

## 2. Core Views & Components

1. **Kanban Board**: 4 drag-and-drop lanes (`Ready`, `In Progress`, `Blocked`, `Closed`) with pagination for older completed tasks.
2. **Table View**: High-density tabular layout with search, sorting, and type filters.
3. **Mind Map & DAG Graph**: Visual node-and-edge hierarchical canvas with:
   - Orientation toggle (`Top-Down` $\leftrightarrow$ `Left-to-Right`).
   - Subtree collapse and expand at task level and root level.
   - Directional dashed dependency curves (`marker-end="url(#arrow)"`).
   - Zoom in, Zoom out, and Reset View canvas controls.
4. **Timeline View**: Chronological audit feed of tickets sorted by creation and modification timestamps.
5. **Settings & Preferences**: Theme accent color selector (Indigo, Emerald, Violet, Amber, Rose, Cyan), high-contrast border mode, start/end date range filtering, settings reset, and documentation link.
6. **Task Detail Drawer**: Markdown renderer for descriptions, acceptance criteria, subtasks list, dependency manager, and timestamped review feedback feed.

---

## 3. CLI Options

```bash
tk webui [directory] [--host HOST] [--port PORT] [--reload] [--version]
```

- `directory`: Initial directory containing `.tickets/` (default: current working directory).
- `--host`: Host IP to bind (default: `127.0.0.1`).
- `--port`: Port number (default: `8000`).
- `--version` / `-v`: Displays version (`tk-webui 0.2.0`).

---

## 4. Backend REST API Endpoints

- `GET /api/check-directory?path=<path>`: Validates folder and checks for `.tickets/`.
- `GET /api/browse?path=<path>`: Returns subfolders with `.tickets` badges for repository browsing.
- `GET /api/tickets?directory=<path>`: Returns array of ticket JSON objects parsed from `.tickets/*.md`.
- `POST /api/tickets`: Creates a new ticket Markdown file.
- `PUT /api/tickets`: Updates ticket fields and metadata.
- `PUT /api/tickets/status`: Transitions ticket status (`open`, `in_progress`, `closed`).
- `POST /api/tickets/notes`: Appends timestamped review notes.
- `POST /api/tickets/dependencies`: Adds a dependency relationship.
- `DELETE /api/tickets/dependencies`: Removes a dependency relationship.
- `POST /api/init`: Initializes `.tickets/` repository.
