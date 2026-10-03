---
title: Dependency Intelligence
description: Understanding Directed Acyclic Graphs (DAG) and dependency tracking in ticket.
---

`ticket` (`tk`) treats task dependencies as a **Directed Acyclic Graph (DAG)**. This ensures tasks are completed in the correct logical sequence without circular deadlocks.

---

## How Dependencies Work

When task `B` depends on task `A`:
1. `B` is considered **blocked** until `A` is closed.
2. `tk ready` will only show `B` after `A` transitions to `closed`.
3. Closing `A` automatically unblocks `B`.

### Adding Dependencies
```bash
# tic-backend-api must finish before tic-frontend-ui can start
tk dep tic-frontend-ui tic-backend-api
```

### Cycle Detection
To prevent circular deadlocks (e.g., A depends on B, B depends on A), `tk` includes native cycle detection:
```bash
tk dep cycle
```

### Viewing Dependency Trees
Inspect recursive upstream and downstream relationships:
```bash
tk dep tree tic-frontend-ui
```
