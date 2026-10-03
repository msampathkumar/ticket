"""Configuration loader and starter template generator for tk-scion-taskforce."""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

DEFAULT_CONFIG: dict[str, Any] = {
    "version": 1,
    "tags": {
        "claim": "taskforce",
        "ignore": "no-taskforce",
        "review": "waiting-for-review",
    },
    "watcher": {
        "poll_interval_seconds": 15,
        "max_concurrent": 10,
        "max_concurrent_per_project": 1,
        "spawn_verify_timeout_seconds": 30,
        "spawn_verify_poll_seconds": 2,
        "spawn_prompt_unblock_seconds": 40,
        "gc_retention_days": 5,
        "auto_pause_on_review": True,
        "auto_wake_on_feedback": True,
    },
    "worker": {
        "prompt_file": "",
        "review_tags": ["pr", "review"],
        "review_ref_prefixes": ["gh-pr-"],
    },
    "provider": {
        "driver": "scion",
        "binary": "scion",
        "profile": "",
        "harness_config": "",
        "branch_prefix": "",
        "extra_start_args": [],
        "extra_resume_args": [],
        "auto_accept_prompts": True,
        "auto_accept_prompt_patterns": ["Yes, I trust this folder"],
        "harness_ready_patterns": ["bypass permissions on", "esc to interrupt"],
        "container_user": "scion",
        "tmux_session": "scion",
    },
    "telemetry": {
        "enabled": True,
        "log_dir": "~/.local/state/tk/scion-taskforce/logs",
        "project_log_symlink": True,
        "traces_file": "otel-traces.jsonl",
        "metrics_file": "otel-metrics.jsonl",
        "daemon_log_file": "daemon.log",
        "worker_logs_dir": "workers",
        "otlp_endpoint": "",
        "rotation": {
            "enabled": True,
            "when": "midnight",
            "max_bytes": 104857600,
            "retention_days": 30,
            "compress": True,
        },
    },
}

STARTER_YAML_TEMPLATE = """# scion-taskforce.yaml — Configuration for tk-scion-taskforce
# Place in:
#   - .tickets/scion-taskforce.yaml          (project-level overrides)
#   - ~/.config/tk/scion-taskforce.yaml      (global defaults)

version: 1

# 1. Ticket Tags (customizable)
#    The task force is OPT-IN: it only picks up ready (unblocked, open) tickets that
#    *you* tagged with `tags.claim`. It never adds that tag on its own.
tags:
  claim: taskforce                # Opt-in tag the USER adds to hand a ticket to the task force
  ignore: no-taskforce            # Tickets with this tag are never picked up (safety override)
  review: waiting-for-review      # Added by the worker when it finishes and pauses for review

# 2. Global Daemon & Concurrency Settings
watcher:
  poll_interval_seconds: 15       # Reconcile interval across registered projects (seconds)
  max_concurrent: 10              # Maximum total running workers across all projects
  max_concurrent_per_project: 1   # Max working tasks per project; next one starts when one finishes.
                                  # SAFETY: SCION mounts the project checkout directly into each pod
                                  # (no per-worker worktree), so concurrent workers in ONE project share
                                  # a working tree and will fight over branches/stashes. Raise above 1
                                  # only if your runtime isolates workspaces.
  spawn_verify_timeout_seconds: 30 # Wait up to N s for a spawned pod to report 'running' before claiming
  spawn_verify_poll_seconds: 2    # Poll interval while verifying a freshly spawned pod
  spawn_prompt_unblock_seconds: 40 # After launch, watch the pod up to N s for interactive harness
                                  # prompts (e.g. Claude's "trust this folder?") and auto-accept them
  gc_retention_days: 5            # Days to retain paused pods after ticket status == closed
  auto_pause_on_review: true      # Automatically pause worker when waiting-for-review is set
  auto_wake_on_feedback: true     # Automatically wake worker when a new review note is added

# 3. Worker Prompt Settings
#    Workers get an auto-generated brief: "implement" for normal tickets, "review" for
#    pull-request tickets (e.g. synced by `tk github sync --prs`). Both explain how to
#    report back even when `tk` is not installed inside the pod.
worker:
  prompt_file: ""                 # Optional path to a custom prompt template. Placeholders:
                                  # {ticket_id} {project_dir} {branch} {ticket_details} {work_type}
                                  # {claim_tag} {review_tag} {external_ref} {ticket_title}
  review_tags: [pr, review]       # A ticket with any of these tags gets the REVIEW brief
  review_ref_prefixes: [gh-pr-]   # ...or whose external-ref starts with one of these prefixes

# 4. Worker Provider Settings (pluggable runtime)
provider:
  driver: scion                   # Orchestrator backend ('scion' today; extensible)
  binary: scion                   # Path or command name for the provider CLI
  profile: ""                     # Optional SCION runtime profile (--profile)
  harness_config: ""              # Optional SCION harness config (--harness-config)
  branch_prefix: ""               # Optional git branch prefix (default: <ticket-id>)
  extra_start_args: []            # Additional flags passed to 'scion start'
  extra_resume_args: []           # Additional flags passed to 'scion resume'
  auto_accept_prompts: true       # Press Enter on known harness start-up prompts inside the pod
  auto_accept_prompt_patterns: ["Yes, I trust this folder"]
  harness_ready_patterns: ["bypass permissions on", "esc to interrupt"]  # Stop watching once seen
  container_user: scion           # User owning the tmux session inside the pod
  tmux_session: scion             # tmux session name used by the scion image

# 5. OpenTelemetry & Local Log Rotation Settings
telemetry:
  enabled: true
  log_dir: ~/.local/state/tk/scion-taskforce/logs
  project_log_symlink: true       # Symlink <project>/.tickets/.scion-taskforce-logs -> global log dir
  traces_file: otel-traces.jsonl
  metrics_file: otel-metrics.jsonl
  daemon_log_file: daemon.log
  worker_logs_dir: workers
  otlp_endpoint: ""               # Optional OTLP HTTP/gRPC collector endpoint
  rotation:
    enabled: true
    when: midnight                # Rotate logs daily at midnight
    max_bytes: 104857600          # Also rotate if active log exceeds 100 MB
    retention_days: 30            # Keep 30 days of rotated logs before automatic deletion
    compress: true                # Gzip rotated log files (.gz)
"""


def global_config_path() -> Path:
    """``$XDG_CONFIG_HOME/tk/scion-taskforce.yaml`` (default ``~/.config/tk/scion-taskforce.yaml``)."""
    base = os.environ.get("XDG_CONFIG_HOME", "").strip()
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "tk" / "scion-taskforce.yaml"


def _parse_scalar(val: str) -> Any:
    val = val.strip()
    if val in ("[]", "[ ]"):
        return []
    if val in ("{}", "{ }"):
        return {}
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "none", "~"):
        return None
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _fallback_parse_yaml(text: str) -> dict[str, Any]:
    """Minimal indentation-aware YAML parser for 2-3 level nested mappings."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for raw_line in text.splitlines():
        line_no_comment = raw_line
        in_single = False
        in_double = False
        for idx, ch in enumerate(raw_line):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif (
                ch == "#"
                and not in_single
                and not in_double
                and (idx == 0 or raw_line[idx - 1].isspace())
            ):
                line_no_comment = raw_line[:idx]
                break

        stripped = line_no_comment.strip()
        if not stripped or ":" not in stripped:
            continue

        indent = len(line_no_comment) - len(line_no_comment.lstrip(" "))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        current_dict = stack[-1][1]
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()

        if not rest:
            new_section: dict[str, Any] = {}
            current_dict[key] = new_section
            stack.append((indent, new_section))
        else:
            current_dict[key] = _parse_scalar(rest)

    return root


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    return _fallback_parse_yaml(text)


def resolve_config_path(
    project_dir: Path | None = None,
    explicit_config: str | None = None,
) -> Path | None:
    if explicit_config:
        candidate = Path(explicit_config).expanduser().resolve()
        if candidate.exists():
            return candidate
    env_cfg = os.environ.get("TK_SCION_TASKFORCE_CONFIG")
    if env_cfg:
        candidate = Path(env_cfg).expanduser().resolve()
        if candidate.exists():
            return candidate
    if project_dir is not None:
        p = Path(project_dir).expanduser().resolve()
        scion_proj_cfg = p / ".scion-taskforce" / "scion-taskforce.yaml"
        if scion_proj_cfg.exists():
            return scion_proj_cfg
        proj_cfg = p / ".tickets" / "scion-taskforce.yaml"
        if proj_cfg.exists():
            return proj_cfg
    global_cfg = global_config_path()
    if global_cfg.exists():
        return global_cfg
    return None


def load_config(
    project_dir: Path | None = None,
    explicit_config: str | None = None,
) -> dict[str, Any]:
    """Load merged configuration following precedence rules."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)

    global_cfg = global_config_path()
    if global_cfg.exists():
        cfg = _deep_merge(cfg, load_yaml_file(global_cfg))

    if project_dir is not None:
        p = Path(project_dir).expanduser().resolve()
        proj_cfg = p / ".tickets" / "scion-taskforce.yaml"
        if proj_cfg.exists():
            cfg = _deep_merge(cfg, load_yaml_file(proj_cfg))
        scion_proj_cfg = p / ".scion-taskforce" / "scion-taskforce.yaml"
        if scion_proj_cfg.exists():
            cfg = _deep_merge(cfg, load_yaml_file(scion_proj_cfg))

    env_cfg = os.environ.get("TK_SCION_TASKFORCE_CONFIG")
    if env_cfg:
        env_path = Path(env_cfg).expanduser().resolve()
        if env_path.exists():
            cfg = _deep_merge(cfg, load_yaml_file(env_path))

    if explicit_config:
        exp_path = Path(explicit_config).expanduser().resolve()
        if exp_path.exists():
            cfg = _deep_merge(cfg, load_yaml_file(exp_path))

    return cfg


def init_config(
    project_dir: Path | None = None,
    global_scope: bool = False,
    force: bool = False,
) -> tuple[Path, int]:
    """Initialize .scion-taskforce/ directory in project or global config."""
    archived_count = 0
    if global_scope:
        target = global_config_path()
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists() and not force:
            return target, 0
        target.write_text(STARTER_YAML_TEMPLATE, encoding="utf-8")
        return target, 0

    import time
    base_dir = Path(project_dir or Path.cwd()).expanduser().resolve()
    scion_dir = base_dir / ".scion-taskforce"
    scion_dir.mkdir(parents=True, exist_ok=True)

    yaml_target = scion_dir / "scion-taskforce.yaml"
    prompt_target = scion_dir / "prompt.md"

    timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())

    for existing_file in [yaml_target, prompt_target]:
        if existing_file.exists():
            if force:
                existing_file.unlink()
            else:
                old_backup = existing_file.with_name(f"{existing_file.name}.{timestamp}.old")
                existing_file.rename(old_backup)
                archived_count += 1

    yaml_target.write_text(STARTER_YAML_TEMPLATE, encoding="utf-8")

    default_prompt_content = (
        "# Default Scion Task Force Prompt Template\n"
        "# Placeholders: {ticket_id}, {ticket_title}, {project_dir}, {branch}, {work_type}, {ticket_details}\n\n"
        "You are an autonomous task force worker assigned to ticket {ticket_id} ({ticket_title}).\n"
        "Working directory: {project_dir} (branch: {branch}).\n\n"
        "### Ticket Details\n{ticket_details}\n"
    )
    prompt_target.write_text(default_prompt_content, encoding="utf-8")

    return yaml_target, archived_count


def uninit_config(
    project_dir: Path | None = None,
    global_scope: bool = False,
) -> tuple[bool, str]:
    """Remove .scion-taskforce/ directory or global config file."""
    if global_scope:
        target = global_config_path()
        if target.exists():
            target.unlink()
            return True, str(target)
        return False, str(target)

    base_dir = Path(project_dir or Path.cwd()).expanduser().resolve()
    scion_dir = base_dir / ".scion-taskforce"
    if scion_dir.is_dir():
        import shutil
        shutil.rmtree(scion_dir)
        return True, str(scion_dir)
    return False, str(scion_dir)
