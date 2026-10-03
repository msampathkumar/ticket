---
title: Web UI Overview
description: Interactive FastAPI & Tailwind Kanban dashboard and DAG mind map for ticket.
---

The Web UI (`tk-webui`) is an optional, high-performance visual dashboard running on port **`8475`** (ASCII for **T** = 84, **K** = 75).

---

### 🖥️ Visual Showcase

| 4-Lane Kanban Board | Interactive Dependency Graph |
| :---: | :---: |
| ![Kanban Board](/images/tk-kanban.png) | ![Mind Map & DAG Graph](/images/tk-mind-map.png) |

| Create & Edit Ticket | Table & Filter View |
| :---: | :---: |
| ![Create & Edit Task](/images/tk-create-page.png) | ![Table View](/images/tk-list-view.png) |

---

### Key UI Features

- **4-Lane Kanban Board**: Fluid drag-and-drop between Ready, In Progress, Blocked, and Closed lanes.
- **Interactive Mind Map & DAG Graph**: Visualize task dependencies, filter by status, toggle top-down or left-to-right layouts, and expand/collapse subtrees.
- **Multi-View Switcher**: Instantly toggle between **Kanban**, **Table View**, **Dependency Tree Graph**, and **Timeline/Gantt View**.
- **In-Place Task Editing**: Edit titles, descriptions, tags, priorities, assignees, design notes, and acceptance criteria in real time.
- **PR-Style Review Comments**: Chronological audit trail for review notes and comments (`Cmd+Enter` to submit).

---

### Launching the Web UI

```bash
# Start foreground server
tk webui

# Or start as a background daemon
tk webui server start
```
Access the dashboard at [http://localhost:8475](http://localhost:8475).
