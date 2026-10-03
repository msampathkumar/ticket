---
title: Daemon Management
description: Managing the background server daemon for tk webui.
---

You can run the Web UI as a persistent background daemon so it is always ready when you need it.

---

### Daemon Commands

```bash
# Start background daemon on http://127.0.0.1:8475
tk webui server start [optional-project-path]

# Inspect daemon PID, URL, and log file path
tk webui server status

# Stop background daemon
tk webui server stop

# Restart daemon
tk webui server restart
```

Logs are automatically rotated and stored locally for debugging.
