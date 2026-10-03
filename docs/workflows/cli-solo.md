---
title: Solo CLI Workflow
description: Fast, offline, zero-dependency task management for individual developers and terminal power users.
---

The **Solo CLI Workflow** provides rapid, offline task tracking for individual developers and terminal power users directly in the shell.

---

## Lifecycle Overview

```mermaid
flowchart LR
    A["tk init<br/>Initialize repo"] --> B["tk create<br/>Capture idea"]
    B --> C["tk ready<br/>Query work"]
    C --> D["tk start<br/>Begin coding"]
    D --> E["tk add-note<br/>Document"]
    E --> F["tk close<br/>Mark complete"]

    style A fill:#6366f1,stroke:#4f46e5,color:#fff
    style B fill:#3b82f6,stroke:#2563eb,color:#fff
    style C fill:#10b981,stroke:#059669,color:#fff
    style D fill:#f59e0b,stroke:#d97706,color:#fff
    style E fill:#8b5cf6,stroke:#7c3aed,color:#fff
    style F fill:#ec4899,stroke:#db2777,color:#fff
```

---

## Step-by-Step Walkthrough

### 1. Initialize Once

Inside your Git project root:

```bash
tk init
```

This creates `.tickets/`. All task metadata is versioned directly with your code.

### 2. Rapid Task Creation

Create tasks with priority, type, and tags directly from the shell:

```bash
tk create "Add SQLite caching layer" -p 1 -t feature --tags database,performance
```

### 3. Check Ready Tasks

Query actionable tasks whose dependencies are satisfied:

```bash
tk ready
```

### 4. Work & Add Notes

Mark the task in progress and record design decisions or progress notes:

```bash
tk start tic-10a
tk add-note tic-10a "Evaluated in-memory cache vs WAL mode; choosing WAL mode."
```

### 5. Close and Unblock

When work is complete, close the task:

```bash
tk close tic-10a
```

Any dependent tasks are automatically unblocked and immediately appear in `tk ready`.
