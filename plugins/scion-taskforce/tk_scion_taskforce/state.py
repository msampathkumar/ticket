"""Worker state store for tk-scion-taskforce (``~/.local/state/tk/scion-taskforce.json``).

Holds one entry per worker (``<project>::<ticket-id>``) plus per-project provider health.
Writers serialise through the per-project lock in ``workers.project_lock``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


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


def load_state() -> dict[str, Any]:
    sfile = get_state_file()
    try:
        data = json.loads(sfile.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}
    data.setdefault("workers", {})
    return data


def save_state(state: dict[str, Any]) -> None:
    sfile = get_state_file()
    sfile.parent.mkdir(parents=True, exist_ok=True)
    tmp_file = sfile.with_suffix(".json.tmp")
    tmp_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    tmp_file.replace(sfile)


def normalize_project_dir(directory: str | Path) -> str:
    resolved = Path(directory).expanduser().resolve()
    if resolved.name == ".tickets":
        resolved = resolved.parent
    return str(resolved)


def known_projects(state: dict[str, Any]) -> list[str]:
    """Projects that have (or had) workers, in stable order."""
    return sorted({str(w.get("project_dir")) for w in state.get("workers", {}).values() if w.get("project_dir")})
