---
title: Web UI & Kanban Workflow
description: Visual task management, sprint planning, and interactive DAG dependency tracking with tk webui.
---

The **Web UI & Kanban Workflow** combines the command-line speed of `tk` with a rich, interactive browser-based dashboard running on port **`8475`**.

---

## 🧭 Visual Lifecycle

```mermaid
flowchart TD
    A["Start Background Daemon\n`tk webui server start`"] --> B["Open http://localhost:8475"]
    B --> C["4-Lane Kanban Board\n(Ready, In Progress, Blocked, Closed)"]
    B --> D["DAG Mind Map Canvas\n(Interactive Dependency Trees)"]
    C --> E["Drag & Drop State Transitions"]
    D --> F["Visualize Critical Path & Blockers"]
    E --> G["Review Comments & Markdown Audit Trail"]
    F --> G

    style A fill:#6366f1,stroke:#4f46e5,color:#fff
    style B fill:#3b82f6,stroke:#2563eb,color:#fff
    style C fill:#10b981,stroke:#059669,color:#fff
    style D fill:#f59e0b,stroke:#d97706,color:#fff
    style E fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style F fill:#ec4899,stroke:#db2777,color:#fff
    style G fill:#06b6d4,stroke:#0891b2,color:#fff
```

---

## 🖥️ Visual Highlights

| 4-Lane Kanban Board | DAG Mind Map Canvas |
| :---: | :---: |
| ![Kanban Board](/images/tk-kanban.png) | ![Mind Map & DAG Graph](/images/tk-mind-map.png) |

---

## 🛠️ Step-by-Step Walkthrough

### 1. Launch the Background Daemon
Keep your web dashboard running persistently without tying up your active shell:
```bash
tk webui server start
```
Check status or logs at any time:
```bash
tk webui server status
```

### 2. Visualize Sprint & Mind Map
Open [http://localhost:8475](http://localhost:8475) in your browser:
- Switch to **Mind Map View** to see dependencies, parent-child task links, and critical paths.
- Switch to **Kanban Board** to drag tasks seamlessly between Ready, In Progress, Blocked, and Closed lanes.

### 3. Collaborative Review
- Open any task drawer to review design notes and acceptance criteria.
- Append chronological audit notes with `Cmd+Enter`.
