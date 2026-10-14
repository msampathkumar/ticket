---
title: Quick Start
description: Initialize a repository, create tasks, manage dependencies, and launch the Web UI.
---

Follow this quick start guide to initialize a repository, create tasks, track dependencies, and launch the Web UI.

---

## Step 1: Initialize a Project

Navigate to your repository and initialize `.tickets/`:

```bash
cd my-project
tk init
```

This creates `.tickets/` with a closed setup ticket and a `.tickets/.gitignore` that keeps lock files and the hook log out of Git. Tickets are plain Markdown files with YAML frontmatter; commit them with your code. (`tk create` also initializes `.tickets/` if it is missing.)

## Step 2: Create Tasks

Create tasks with priority and tags:

```bash
tk create "Implement user authentication" \
  -d "Add JWT-based auth to FastAPI backend" \
  -p 1 \
  --tags backend,security
# myp-a1b2c3

tk create "Add login page" --tags frontend
# myp-d4e5f6
```

`tk` prints the generated ID: a prefix from the folder name plus a 6-character random hash. Commands accept partial IDs (`tk show a1b`).

## Step 3: Add a Dependency

The login page needs the auth work first:

```bash
tk dep myp-d4e5f6 myp-a1b2c3
```

## Step 4: Check Actionable Work (`tk ready`)

`tk ready` lists tickets whose dependencies are all closed:

```bash
tk ready
```

Only `myp-a1b2c3` is listed; `tk blocked` shows `myp-d4e5f6` waiting on it.

## Step 5: Claim & Work on the Task

Mark the task as in progress:

```bash
tk start myp-a1b2c3
```

When several agents or people share the queue, claim instead. The claim sets the assignee and status in one locked step and exits `3` if someone else already holds the ticket:

```bash
tk start myp-a1b2c3 --claim
```

Add progress notes:

```bash
tk add-note myp-a1b2c3 "Completed token generation logic and unit tests."
```

## Step 6: Close the Task & Unblock Dependents

```bash
tk close myp-a1b2c3
tk ready    # myp-d4e5f6 is now ready
```

## Step 7: Launch the Web UI (Optional Plugin)

If you installed the Web UI (`./install.sh --full` or `--webui`), open the Kanban board and DAG Mind Map:

```bash
tk webui
```

Open [http://localhost:8475](http://localhost:8475) in your browser.
