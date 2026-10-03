"""Singleton multi-project daemon state and lifecycle manager for tk-scion-taskforce."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tk_scion_taskforce.telemetry import utc_now_iso


def get_state_dir() -> Path:
    env_state = os.environ.get("TK_SCION_TASKFORCE_STATE_DIR")
    if env_state:
        return Path(env_state).expanduser().resolve()
    return (Path.home() / ".local" / "state" / "tk").resolve()


def get_state_file() -> Path:
    env_file = os.environ.get("TK_SCION_TASKFORCE_STATE_FILE")
    if env_file:
        return Path(env_file).expanduser().resolve()
    return get_state_dir() / "scion-taskforce.json"


def is_pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _default_state() -> dict[str, Any]:
    return {
        "pid": None,
        "started_at": None,
        "projects": [],
        "workers": {},
    }


def load_state() -> dict[str, Any]:
    sfile = get_state_file()
    if not sfile.exists():
        return _default_state()
    try:
        data = json.loads(sfile.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return _default_state()
        data.setdefault("pid", None)
        data.setdefault("started_at", None)
        data.setdefault("projects", [])
        data.setdefault("workers", {})
        if data["pid"] and not is_pid_alive(int(data["pid"])):
            data["pid"] = None
            data["started_at"] = None
        return data
    except (OSError, ValueError, json.JSONDecodeError):
        return _default_state()


def save_state(state: dict[str, Any]) -> None:
    sfile = get_state_file()
    print(f"📝 Updating global daemon state registry at `{sfile}`...")
    sfile.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = sfile.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp_file.replace(sfile)
    print(f"✅ State registry updated successfully (watched projects: {len(state.get('projects', []))}, active workers: {len(state.get('workers', {}))}).")


def normalize_project_dir(directory: str | Path) -> str:
    resolved = Path(directory).expanduser().resolve()
    if resolved.name == ".tickets":
        resolved = resolved.parent
    return str(resolved)


def add_project(directory: str | Path) -> str:
    proj = normalize_project_dir(directory)
    state = load_state()
    projects: list[str] = state.get("projects", [])
    if proj not in projects:
        projects.append(proj)
        state["projects"] = projects
        save_state(state)
    return proj


def remove_project(directory: str | Path) -> bool:
    proj = normalize_project_dir(directory)
    state = load_state()
    projects: list[str] = state.get("projects", [])
    if proj in projects:
        projects.remove(proj)
        state["projects"] = projects
        save_state(state)
        return True
    return False


def list_projects() -> list[str]:
    state = load_state()
    return list(state.get("projects", []))


def start_server(
    directory: str | None = None,
    explicit_config: str | None = None,
    poll_interval: int | None = None,
    max_concurrent: int | None = None,
) -> int:
    target_proj = add_project(directory or Path.cwd())
    state = load_state()
    existing_pid = state.get("pid")

    if existing_pid and is_pid_alive(int(existing_pid)):
        print(f"⚠️  tk-scion-taskforce daemon is already running (PID: {existing_pid})")
        print(f"📁 Registered project: {target_proj}")
        print(f"📊 Total watched projects: {len(state.get('projects', []))}")
        return 0

    plugin_root = str(Path(__file__).resolve().parent.parent)
    env = os.environ.copy()
    existing_py = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = f"{plugin_root}:{existing_py}" if existing_py else plugin_root

    cmd: list[str] = [
        sys.executable,
        "-m",
        "tk_scion_taskforce.cli",
    ]
    if explicit_config:
        cmd.extend(["--config", explicit_config])
    cmd.extend(["watch", target_proj])
    if poll_interval is not None:
        cmd.extend(["--interval", str(poll_interval)])
    if max_concurrent is not None:
        cmd.extend(["--max-concurrent", str(max_concurrent)])

    log_dir = get_state_dir() / "scion-taskforce" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = log_dir / "daemon-stdio.log"

    with open(stdout_log, "a", encoding="utf-8") as log_fd:
        proc = subprocess.Popen(
            cmd,
            stdout=log_fd,
            stderr=subprocess.STDOUT,
            env=env,
            start_new_session=True,
        )

    time.sleep(0.4)
    if not is_pid_alive(proc.pid):
        print("❌ Failed to start tk-scion-taskforce daemon. Check log for details:")
        print(f"📄 Log: {stdout_log}")
        return 1

    state = load_state()
    state["pid"] = proc.pid
    state["started_at"] = utc_now_iso()
    if target_proj not in state["projects"]:
        state["projects"].append(target_proj)
    save_state(state)

    print(f"🚀 tk-scion-taskforce daemon started in background (PID: {proc.pid})")
    print(f"📁 Registered project: {target_proj}")
    print(f"📊 Watched projects:   {len(state['projects'])}")
    print(f"📄 Telemetry & logs:   {log_dir}")
    print("💡 Manage daemon: 'tk scion-taskforce status' or 'tk scion-taskforce stop'")
    return 0


def stop_server() -> int:
    state = load_state()
    pid = state.get("pid")
    if not pid or not is_pid_alive(int(pid)):
        state["pid"] = None
        state["started_at"] = None
        save_state(state)
        print("ℹ️  tk-scion-taskforce daemon is not running.")
        return 0

    pid_int = int(pid)
    print(f"🛑 Stopping tk-scion-taskforce daemon (PID: {pid_int})...")
    try:
        os.kill(pid_int, signal.SIGTERM)
        for _ in range(30):
            if not is_pid_alive(pid_int):
                break
            time.sleep(0.1)
        if is_pid_alive(pid_int):
            os.kill(pid_int, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass

    state = load_state()
    state["pid"] = None
    state["started_at"] = None
    save_state(state)
    print("✅ tk-scion-taskforce daemon stopped.")
    return 0


def stop_project(directory: str | Path, pause_workers: bool = True, explicit_config: str | None = None) -> int:
    """Stop the task force for ONE project: pause its running workers, unregister it,
    and shut the global daemon down if no watched projects remain."""
    proj = normalize_project_dir(directory)
    state = load_state()
    workers: dict[str, dict[str, Any]] = state.get("workers", {})

    paused = 0
    if pause_workers:
        running = [w for w in workers.values() if w.get("project_dir") == proj and w.get("state") == "running"]
        if running:
            # Local import to avoid a circular import at module load time.
            from tk_scion_taskforce.config import load_config
            from tk_scion_taskforce.providers import get_provider

            cfg = load_config(project_dir=Path(proj), explicit_config=explicit_config)
            provider = get_provider(cfg)
            for w in running:
                tid = str(w.get("ticket_id", ""))
                if provider.pause(proj, tid):
                    w["state"] = "paused"
                    w["paused_at"] = utc_now_iso()
                    paused += 1
                else:
                    print(f"⚠️  Could not pause worker {tid}: {provider.last_error}")
            save_state(state)

    removed = remove_project(proj)
    if removed:
        print(f"🛑 Task force stopped for project: {proj} (paused {paused} worker(s), unregistered)")
    else:
        print(f"ℹ️  Project was not registered with the task force: {proj}")

    if not list_projects():
        print("ℹ️  No watched projects remain — stopping the global daemon.")
        return stop_server()
    return 0


def status_server(log_dir: Path | None = None) -> int:
    state = load_state()
    pid = state.get("pid")
    projects: list[str] = state.get("projects", [])
    workers: dict[str, dict[str, Any]] = state.get("workers", {})

    running_count = sum(1 for w in workers.values() if w.get("state") == "running")
    paused_count = sum(1 for w in workers.values() if w.get("state") == "paused")
    error_count = sum(1 for w in workers.values() if w.get("state") == "error")
    health: dict[str, dict[str, Any]] = state.get("project_health", {})

    if pid and is_pid_alive(int(pid)):
        print("● tk-scion-taskforce daemon is running")
        print(f"  PID:              {pid}")
        print(f"  Started:          {state.get('started_at')}")
    else:
        print("○ tk-scion-taskforce daemon is stopped.")

    print(f"  Watched projects: {len(projects)}")
    for p in projects:
        h = health.get(p)
        if h is None:
            marker = "  "
        elif h.get("ok"):
            marker = "✅"
        else:
            marker = "❌"
        print(f"    {marker} {p}")
        if h is not None and not h.get("ok"):
            print(f"       provider unavailable: {str(h.get('message', ''))[:120]}")
    print(
        f"  Workers:          {running_count} running, {paused_count} paused (waiting-for-review)"
        + (f", {error_count} error" if error_count else "")
    )
    if log_dir:
        print(f"  Logs directory:   {log_dir}")
    return 0


def restart_server(
    directory: str | None = None,
    explicit_config: str | None = None,
) -> int:
    stop_server()
    time.sleep(0.3)
    return start_server(directory=directory, explicit_config=explicit_config)
