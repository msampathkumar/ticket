---
id: tic-822k
status: in_progress
deps: []
links: []
created: 2026-10-01T09:58:53Z
type: task
priority: 1
assignee: Sampath Kumar
tags: [taskforce, waiting-for-review]
---
# Scion Task Force

Task: Create a design document for a new plugin. This plugin works in combination with Ticketing tool and SCION. Tickets provide great UI for creating tasks but without workers, there is no real activity happending. So we will use SCION (https://github.com/GoogleCloudPlatform/scion) for this. You can assume that user to install SCION by themslevers and keep it running.

Requirement:
Asynchronous ticket identification system That can find tickets as and when they are created and create see on worker nodes on the project where the task is created and run the SCION worker agents to complete the job and report back to the system using the TK ticket tool The Sion Worker or Docker instance or Podman instance that is created for this job will have the same task ID as the ticket ID once task is completed the agent system will report back to the task with the latest update and mark it for review the status will be kept as in progress with label `waiting for review`.

This system should also understand that once feedback is give, its passes it the worker instance.

Once a task is completed, the worker instance should pause. If the task is marked as completed and older than 5 days, the pod can be removed.

That can find tickets as and when they are created and create see on worker nodes on the project where the task is created and run the Scion worker agents to complete the job and report back to the system using the TK ticket tool The Sion Worker or Docker instance or Podman instance that is created for this job will have the same task ID as the ticket ID once task is completed the agent system will report back to the task with the latest update and mark it for review the status will be kept as in progress

It is possible that, user may unpause the scion agent worker to have deeper conversation.


## Notes

**2026-10-01T10:33:00Z**

Created plugins/scion/SCION-SPEC.md defining the architecture, CLI commands, 1:1 SCION worker lifecycle, NOSCION/no-scion opt-out, cloudcode claiming tag, waiting-for-review auto-pause, feedback wake loop, interactive attach, and 5-day closed pod garbage collection.

**2026-10-01T10:37:23Z**

Updated plugins/scion/SCION-SPEC.md to include OpenTelemetry (OTel) tracing, metrics, and structured local file logging under .tickets/.scion-logs/ (otel-traces.jsonl, otel-metrics.jsonl, daemon.log, and workers/<id>.log) along with 'tk scion trace <id>' and 'tk scion logs <id> --otel' commands.

**2026-10-01T11:08:09Z**

Updated default claim tag to 'taskforce' and added short user-configurable YAML configuration specification (.tickets/scion.yaml and plugins/scion/scion.yaml).

**2026-10-01T11:23:23Z**

Renamed plugin folder to plugins/scion-taskforce/ (SCION-TASKFORCE-SPEC.md, scion-taskforce.yaml) and binary/command to tk-scion-taskforce / ticket-scion-taskforce (tk scion-taskforce).

**2026-10-01T11:26:08Z**

Updated design spec to plugins/taskforce/TASKFORCE-SPEC.md and plugins/taskforce/taskforce.yaml (command: tk taskforce, binary: tk-taskforce) implemented in Python 3.9+ with a pluggable WorkerProvider interface so SCION (default provider.driver: scion) can be swapped for any future orchestrator without changing CLI commands, tags, or telemetry.

**2026-10-01T11:42:13Z**

Standardized plugin naming to 'scion-taskforce' (plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md, plugins/scion-taskforce/scion-taskforce.yaml, binary tk-scion-taskforce / ticket-scion-taskforce) and designed a single global multi-project daemon instance (~/.local/state/tk/scion-taskforce.json) matching tk-webui.

**2026-10-01T12:08:45Z**

Added 30-day log rotation (telemetry.rotation: retention_days 30, midnight rotation, 100MB size cap, gzip) to SCION-TASKFORCE-SPEC.md Section 6.6 and scion-taskforce.yaml; registered plugin in plugins/README.md and AGENTS.md.
