---
title: SCION Task Force
description: Autonomous multi-agent worker orchestration plugin for ticket.
---

The **SCION Task Force** (`tk-scion-taskforce`) is an optional standalone orchestrator plugin that manages autonomous coding workers mapped 1:1 to tickets.

---

### How It Works

1. **Watchdog Daemon**: A single global daemon (`~/.local/state/tk/scion-taskforce.json`) watches `tk ready` tickets tagged with `taskforce`.
2. **Worker Spawning**: Automatically spawns a SCION coding worker mapped to the ticket ID.
3. **Review Pause**: Automatically pauses workers on `waiting-for-review`, relays feedback, and emits OpenTelemetry to local rotating logs (30-day retention).

Install via:
```bash
./install.sh --scion-taskforce
```
