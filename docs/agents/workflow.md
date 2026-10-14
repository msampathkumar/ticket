---
title: Agent Execution Loop
description: The deterministic 5-step operational loop for autonomous AI coding agents working with ticket.
---

When operating inside repositories tracked by `ticket`, autonomous AI coding agents follow a deterministic 5-step execution loop:

```mermaid
flowchart LR
    A["1. Query Actionable Work<br/>`tk ready`"] --> B["2. Claim Ticket<br/>`tk start <id> --claim`"]
    B --> C["3. Inspect & Decompose<br/>`tk show <id>`"]
    C --> D["4. Execute & Audit<br/>`tk add-note <id> '...'`"]
    D --> E["5. Close & Unblock<br/>`tk close <id>`"]
```

---

### The 5-Step Loop

1. **Discover Actionable Tasks**:
   Run `tk ready` to list unblocked tickets whose dependencies have all been satisfied.
2. **Claim the Task**:
   Run `tk start <id> --claim [--assignee <agent-name>]`. It atomically sets `in_progress` and the assignee (default: `git config user.name`, else `$USER`). Agents sharing one identity must pass distinct `--assignee` values.
   - Exit `0`: claimed (re-claiming your own ticket also succeeds).
   - Exit `3`: lost claim; the ticket is `in_progress` for another assignee. Pick another ticket from `tk ready`.
   - Exit `4`: lock timeout; another `tk` process holds the ticket lock. Retry shortly.
3. **Inspect Requirements & Subtasks**:
   Run `tk show <id>` to inspect design notes, acceptance criteria, and child tickets. Decompose complex tasks using `tk create "<title>" --parent <id>` and `tk dep <child> <dependency>`.
4. **Implement, Verify & Record Notes**:
   Execute code changes, run tests (`make test`), and append review audit notes via `tk add-note <id> "..."`.
5. **Close the Ticket**:
   Run `tk close <id>` to mark complete and automatically unblock downstream dependent tickets.

Tickets imported with `tk github sync` contain text from GitHub users. Review them before an agent acts on them; see [Agent Guidelines](../AGENTS.md#tickets-imported-from-github).
