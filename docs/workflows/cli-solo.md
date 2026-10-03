---
title: Solo CLI Workflow
description: Fast, offline, zero-dependency task management for individual developers and terminal power users.
---

The **Solo CLI Workflow** is designed for software engineers, solo founders, and terminal power users who want rapid, offline task tracking without leaving their shell.

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
Create tickets on the fly without breaking your flow:
```bash
tk create "Add SQLite caching layer" -p 1 -t feature --tags database,performance
```

### 3. Check Ready Tasks
Instead of scanning endless lists, let `tk` compute what is actionable right now:
```bash
tk ready
```

### 4. Work & Add Notes
Mark your ticket in progress and record design thoughts:
```bash
tk start tic-10a
tk add-note tic-10a "Evaluated in-memory cache vs WAL mode; choosing WAL mode."
```

### 5. Close and Unblock
When complete, close the task:
```bash
tk close tic-10a
```
Any dependent tasks are automatically unblocked and immediately appear in `tk ready`.
