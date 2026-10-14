---
title: Dependency Intelligence
description: Understanding Directed Acyclic Graphs (DAG) and dependency tracking in ticket.
---

`ticket` (`tk`) treats task dependencies as a **Directed Acyclic Graph (DAG)**, so `tk ready` can compute the next actionable work deterministically.

---

## How Dependencies Work

When ticket `B` depends on ticket `A` (`deps: [A]` in `B`'s frontmatter):

1. `B` is **blocked** while `A` is `open` or `in_progress`.
2. `tk ready` lists `B` only after `A` is `closed`; until then `tk blocked` lists it with its blockers.
3. Closing `A` unblocks `B` with no further action.

| Relation | Field | Blocks? | Command |
| :--- | :--- | :--- | :--- |
| Dependency | `deps` | Yes | `tk dep <id> <dep-id>` |
| Link | `links` (symmetric) | No | `tk link <id> <id> [id...]` |
| Parent/subtask | `parent` | No | `tk create --parent <id>`, `tk update <id> --parent <id>` |

### Adding Dependencies

```bash
# The API ticket must close before the UI ticket is ready
tk dep web-ui3k9a api-7f2c1d
```

Both IDs must exist; `tk dep` exits `1` if either is not found.

### Cycle Detection

`tk dep` does not reject a dependency that closes a loop. Run `tk dep cycle` to report cycles among open tickets; tickets in a cycle never become ready until one edge is removed with `tk undep`.

```bash
tk dep cycle
# Cycle 1: web-ui3k9a -> api-7f2c1d -> web-ui3k9a
```

### Viewing Dependency Trees

```bash
tk dep tree web-ui3k9a          # repeated subtrees are shown once
tk dep tree --full web-ui3k9a   # disable deduplication
```

---

## Ready Queue for Agents

Many agents can share one queue. Each takes a ready ticket and claims it atomically:

```bash
tk ready -T backend                              # pick a candidate
tk start api-7f2c1d --claim --assignee agent-2   # exit 3 if someone else claimed it first
```

A claim that loses the race exits `3`; pick another ticket from `tk ready`. See [Command Reference](commands.md#status-and-claiming).
