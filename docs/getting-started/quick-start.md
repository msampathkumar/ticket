---
title: Quick Start
description: Get up and running with ticket (tk) in 60 seconds.
---

Follow this 60-second quick start guide to initialize your first project, create tasks, manage dependencies, and launch the Web UI.

---

### Step 1: Initialize a Project
Navigate to your repository and initialize `.tickets/`:
```bash
cd my-project
tk init
```
This creates a `.tickets/` directory where all tasks are stored as plain Markdown files with YAML frontmatter.

### Step 2: Create a Task
Create your first task with priority and tags:
```bash
tk create "Implement user authentication" \
  -d "Add JWT-based auth to FastAPI backend" \
  -p 1 \
  --tags backend,security
```
`tk` prints the generated task ID (e.g., `tic-abc1`).

### Step 3: Check Actionable Work (`tk ready`)
Run `tk ready` to list unblocked tasks whose dependencies are fully satisfied:
```bash
tk ready
```

### Step 4: Claim & Work on the Task
Mark the task as in progress:
```bash
tk start tic-abc1
```
Add review notes or progress logs:
```bash
tk add-note tic-abc1 "Completed token generation logic and unit tests."
```

### Step 5: Close the Task & Unblock Dependents
When finished, close the task:
```bash
tk close tic-abc1
```
This automatically updates the status and unblocks any downstream dependent tasks.

### Step 6: Launch the Interactive Web UI
Launch the 4-lane Kanban board and DAG Mind Map:
```bash
tk webui
```
Open [http://localhost:8475](http://localhost:8475) in your browser.
