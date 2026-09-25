import os
import sys
import time
import signal
import json
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

STATE_DIR = Path.home() / ".local" / "state" / "tk"
PID_FILE = STATE_DIR / "webui.json"
LOG_FILE = STATE_DIR / "webui.log"
DEFAULT_PORT = 8475  # ASCII T (84) & K (75) ;)


def _ensure_state_dir():
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _is_pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_server_info() -> Optional[Dict[str, Any]]:
    if not PID_FILE.exists():
        return None
    try:
        with open(PID_FILE, "r") as f:
            data = json.load(f)
        pid = data.get("pid")
        if pid and _is_pid_alive(pid):
            return data
        else:
            # Stale PID file
            PID_FILE.unlink(missing_ok=True)
            return None
    except Exception:
        PID_FILE.unlink(missing_ok=True)
        return None


def start_server(directory: str, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> int:
    _ensure_state_dir()
    existing = get_server_info()
    if existing:
        print(f"⚠️  tk-webui server is already running (PID: {existing['pid']})")
        print(f"🌐 URL: http://{existing.get('host', '127.0.0.1')}:{existing.get('port', DEFAULT_PORT)}")
        print(f"📁 Directory: {existing.get('directory', 'unknown')}")
        return 0

    target_dir = os.path.abspath(os.path.expanduser(directory))
    cmd = [
        sys.executable,
        "-m",
        "tk_webui.main",
        target_dir,
        "--host",
        host,
        "--port",
        str(port),
    ]

    log_fd = open(LOG_FILE, "a")
    proc = subprocess.Popen(
        cmd,
        stdout=log_fd,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    # Allow startup initialization
    time.sleep(0.5)

    if not _is_pid_alive(proc.pid):
        print("❌ Failed to start tk-webui server. Check log for details:")
        print(f"📄 Log: {LOG_FILE}")
        return 1

    server_data = {
        "pid": proc.pid,
        "host": host,
        "port": port,
        "directory": target_dir,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    with open(PID_FILE, "w") as f:
        json.dump(server_data, f, indent=2)

    print(f"🚀 tk-webui server started in background (PID: {proc.pid})")
    print(f"🌐 Access at: http://{host}:{port}")
    print(f"📁 Project: {target_dir}")
    print(f"📄 Log output: {LOG_FILE}")
    print("💡 Manage server: 'tk webui server status' or 'tk webui server stop'")
    return 0


def stop_server() -> int:
    info = get_server_info()
    if not info:
        print("ℹ️  tk-webui server is not running.")
        return 0

    pid = info["pid"]
    print(f"🛑 Stopping tk-webui server (PID: {pid})...")

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(30):
            if not _is_pid_alive(pid):
                break
            time.sleep(0.1)
        if _is_pid_alive(pid):
            os.kill(pid, signal.SIGKILL)
    except (OSError, ProcessLookupError):
        pass

    PID_FILE.unlink(missing_ok=True)
    print("✅ tk-webui server stopped.")
    return 0


def status_server() -> int:
    info = get_server_info()
    if info:
        print("● tk-webui server is running")
        print(f"  PID:        {info['pid']}")
        print(f"  URL:        http://{info.get('host', '127.0.0.1')}:{info.get('port', DEFAULT_PORT)}")
        print(f"  Directory:  {info.get('directory')}")
        print(f"  Started:    {info.get('started_at')}")
        print(f"  Log file:   {LOG_FILE}")
        return 0
    else:
        print("○ tk-webui server is stopped.")
        return 0


def restart_server(directory: str, host: str = "127.0.0.1", port: int = DEFAULT_PORT) -> int:
    stop_server()
    time.sleep(0.5)
    return start_server(directory, host, port)
