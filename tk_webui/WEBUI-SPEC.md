# Web UI Plugin Specification (WEBUI-SPEC.md)

- **Plugin Name**: `tk-webui`
- **Command**: `tk webui`
- **Version**: `0.4.0`
- **Installation**: Included in Full Installation (`./install.sh --full` or `./install.sh --webui`)

---

## 1. Overview

`tk-webui` is the official modern web application and review dashboard for `tk`. It runs a local FastAPI web server serving a vanilla HTML5/JavaScript application with Tailwind CSS and Marked.js. All frontend libraries are pinned copies in `static/vendor/` (versions and sha256 in [static/vendor/README.md](static/vendor/README.md)), so the UI works offline. Views use the full window width on large screens.

---

## 2. Core Views & Components

1. **Kanban Board**: 4 drag-and-drop lanes (`Ready`, `In Progress`, `Blocked`, `Closed`) with pagination for older completed tasks. Blocked state matches core `tk blocked` / `tk ready` (see 5.3).
2. **Table View**: High-density tabular layout with search, sorting, type filters, and 4-sided active theme border highlights on row hover.
3. **Mind Map & DAG Graph**: Visual node-and-edge hierarchical canvas with:
   - Orientation toggle (`Top-Down` $\leftrightarrow$ `Left-to-Right`).
   - Multi-select status filtering (`Ready`, `In Progress`, `Blocked`, `Closed`) with active counter badges.
   - Subtree collapse and expand at task level and root level.
   - Directional dashed dependency curves (`marker-end="url(#arrow)"`).
   - Zoom in, Zoom out, and Reset View canvas controls.
4. **Timeline View**: Chronological audit feed of tickets sorted by creation and modification timestamps.
5. **Settings & Preferences**: Theme accent color selector (Indigo, Emerald, Violet, Amber, Rose, Cyan), Typography preferences (Font Family: System Sans, Inter, Monospace, Serif; Font Size: Small 14px, Default 16px, Large 18px, Extra Large 20px), high-contrast border mode with hover preservation, start/end date range filtering, settings reset, and documentation link.
6. **Task Detail Drawer**: Markdown renderer (Marked, sanitised with DOMPurify) for descriptions, acceptance criteria, parent task selector & subtask hierarchy linking/unlinking, symmetric links manager, dependency manager, and timestamped review feedback feed.
7. **Auto-Refresh**: While the tab is visible, the UI polls `GET /api/tickets/version` every 3s and refetches tickets when it changes, so CLI and agent edits appear without a manual refresh. Refreshes wait while the new/edit ticket form is open or a card is being dragged.

### Visual Interface Showcase

| 4-Lane Kanban Board | Interactive Dependency Graph |
| :---: | :---: |
| ![Kanban Board](../../docs/images/tk-kanban.png) | ![Mind Map & DAG Graph](../../docs/images/tk-mind-map.png) |

| Table & Filter View | Create & Edit Ticket |
| :---: | :---: |
| ![Table View](../../docs/images/tk-list-view.png) | ![Create & Edit Task](../../docs/images/tk-create-page.png) |

| Settings & Themes |
| :---: |
| ![Settings](../../docs/images/tk-settings.png) |

---

## 3. CLI & Server Commands

### 3.1 Foreground Server
```bash
tk webui [directory] [--host HOST] [--port PORT] [--reload] [--version]
```

- `directory`: Initial directory containing `.tickets/` (default: current working directory). The browser opens, in order: the `?dir=` URL parameter, else this directory (from `GET /api/config`), else the last project opened in the browser (only when the server was started without the CLI).
- `--host`: Host IP to bind (default: `127.0.0.1`). The value is added to the Host allowlist; `0.0.0.0` / `::` allow any Host (see 5.1).
- `--port`: Port number (default: `8475`, derived from ASCII values for **T** = 84, **K** = 75).
- `--reload`: Reload on code change (development only).
- `--version` / `-v`: Displays version and project details (`tk-webui 0.4.0`).

### 3.2 Background Daemon Server (`tk webui server` & shortcuts)
```bash
# Daemon management
tk webui server start [directory] [--host HOST] [--port PORT]   # Start daemon in background
tk webui server status                            # Check status, URL, PID, and logs
tk webui server stop                              # Stop background daemon
tk webui server restart [directory]               # Restart background daemon

# Direct shortcuts
tk webui start [directory]                        # Shortcut for server start
tk webui status                                   # Shortcut for server status
tk webui stop                                     # Shortcut for server stop
tk webui restart [directory]                      # Shortcut for server restart
```

State files and logs are managed under `~/.local/state/tk/`:
- PID file: `~/.local/state/tk/webui.json` (`pid`, `host`, `port`, `directory`, `started_at`)
- Daemon log: `~/.local/state/tk/webui.log` (appended, not rotated)
- Project registry: `~/.local/state/tk/projects.json`, shared with core `tk init`: `{"projects": [...]}`, 2-space indent, written atomically (temp file + rename). Entries without `.tickets/` are hidden from the switcher but kept in the file.

Daemon behaviour:
- `start` fails immediately if the port already accepts connections. It then polls until the server listens (10s timeout). Early exit or timeout prints the reason and log path and returns non-zero; on timeout the child is terminated.
- `stop` / `status` treat `webui.json` as live only if the PID is alive and its command line contains `tk_webui` and `--port <port>`. Otherwise the file is removed and no signal is sent. `stop` sends SIGTERM, waits 3s, and re-checks identity before SIGKILL.

---

## 4. Backend REST API Endpoints

- `GET /api/config`: Returns `{"initial_dir": <path|null>}`, the directory the CLI was launched for (`null` without the CLI).
- `GET /api/projects`: Returns `{"projects": [...]}`, registered projects that currently contain `.tickets/`.
- `POST /api/projects`: Body `{"path": <path>}`; registers a project (most recent first).
- `GET /api/check-directory?path=<path>`: Validates folder and checks for `.tickets/`.
- `GET /api/browse?path=<path>`: Returns subfolders with `.tickets` badges for repository browsing.
- `GET /api/tickets?directory=<path>`: Returns array of ticket JSON objects parsed from `.tickets/*.md`.
- `GET /api/tickets/version?directory=<path>`: Returns `{"version": <string|null>}`, a change fingerprint (file count and mtimes of `.tickets/*.md`); `null` without `.tickets/`.
- `POST /api/tickets`: Creates a new ticket Markdown file.
- `PUT /api/tickets`: Updates ticket fields and metadata.
- `PUT /api/tickets/status`: Transitions ticket status (`open`, `in_progress`, `closed`).
- `POST /api/tickets/notes`: Appends timestamped review notes.
- `POST /api/tickets/dependencies`: Adds a dependency relationship.
- `DELETE /api/tickets/dependencies`: Removes a dependency relationship.
- `POST /api/tickets/links`: Adds a symmetric relational link between two tickets.
- `DELETE /api/tickets/links`: Removes a symmetric relational link between two tickets.
- `POST /api/init`: Initializes `.tickets/` repository.

---

## 5. Security & Semantics

### 5.1 Security Model

The server has no authentication and acts with the user's file permissions, so it accepts only local, same-origin requests:

- Binds to `127.0.0.1` by default.
- `TrustedHostMiddleware` allows Host `127.0.0.1`, `localhost` and the configured `--host`; other Hosts get `400` (DNS-rebinding defence). Binding `0.0.0.0` or `::` allows any Host and exposes the API to the network.
- No CORS middleware: the UI is same-origin, so browsers block cross-origin reads.
- Non-`GET`/`HEAD`/`OPTIONS` requests whose `Origin` header does not match `Host` get `403` (CSRF defence).
- Markdown is rendered with Marked and sanitised with DOMPurify; other ticket fields are HTML-escaped before insertion.
- No runtime CDN loads; vendored assets are pinned and hashed (`static/vendor/README.md`).

### 5.2 Auto-Refresh

See section 2, item 7. The UI polls `GET /api/tickets/version` every 3s while the tab is visible; deferred while the ticket form is open or a card is dragged.

### 5.3 Blocked / Ready Semantics

Computed in `tk_cli.get_all_tickets`, matching core `cmd_ready` / `cmd_blocked`:

- Only `open` and `in_progress` tickets can be blocked.
- A dependency blocks unless its status is exactly `closed`; a dependency ID with no matching ticket blocks.
- `blocked_by` lists the unresolved dependency IDs.
- Parity with `tk ready` / `tk blocked` is covered by `features/webui_blocked_state.feature`.
