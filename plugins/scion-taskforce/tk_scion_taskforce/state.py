"""Worker state store for tk-scion-taskforce (``~/.local/state/tk/scion-taskforce.json``).

Holds one entry per worker (``<project>::<ticket-id>``) plus per-project provider health.
The file is shared by all projects, so every read-modify-write runs under ``state_lock()``
(taken inside the per-project ``workers.project_lock``).
"""

from __future__ import annotations

import fcntl
import json
import os
import shutil
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class StateError(RuntimeError):
    """The state file exists but cannot be parsed; a backup copy was written next to it."""


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
        raw = sfile.read_text(encoding="utf-8")
    except FileNotFoundError:
        raw = ""
    data: Any = {}
    if raw.strip():
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if not isinstance(data, dict):
            backup = sfile.with_name(f"{sfile.name}.corrupt-{time.strftime('%Y%m%dT%H%M%S')}")
            shutil.copy2(sfile, backup)
            raise StateError(
                f"worker state file {sfile} is not valid JSON; a copy is at {backup}. "
                "Fix or delete the file, then run `tk scion-taskforce sync`."
            )
    data.setdefault("workers", {})
    return data


def save_state(state: dict[str, Any]) -> None:
    sfile = get_state_file()
    sfile.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=sfile.parent, prefix=f".{sfile.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(state, indent=2) + "\n")
        os.replace(tmp_name, sfile)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


@contextmanager
def state_lock() -> Iterator[None]:
    """Serialise read-modify-write of the shared state file across all projects and processes."""
    # shortcut: one lock for every project, so a slow spawn in one project delays hook runs in
    # others; split the state file per project when parallel multi-project dispatch matters.
    sfile = get_state_file()
    sfile.parent.mkdir(parents=True, exist_ok=True)
    with open(sfile.with_name(sfile.name + ".lock"), "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield  # closing the file releases the flock


def normalize_project_dir(directory: str | Path) -> str:
    resolved = Path(directory).expanduser().resolve()
    if resolved.name == ".tickets":
        resolved = resolved.parent
    return str(resolved)


def known_projects(state: dict[str, Any]) -> list[str]:
    """Projects that have (or had) workers, in stable order."""
    return sorted({str(w.get("project_dir")) for w in state.get("workers", {}).values() if w.get("project_dir")})
