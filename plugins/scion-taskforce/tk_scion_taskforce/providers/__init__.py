"""Abstract WorkerProvider interface and provider registry for tk-scion-taskforce."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class WorkerStatus:
    worker_id: str      # 1:1 with ticket_id (e.g. "tic-a1b2")
    project_dir: str    # Project root path
    state: str          # "running" | "paused" | "stopped" | "error" | "unknown"
    branch: str | None = None
    last_command: str | None = None

    @property
    def is_running(self) -> bool:
        return self.state == "running"


@dataclass
class ProviderResult:
    ok: bool
    message: str = ""


class WorkerProvider(ABC):
    """Abstract interface for task force worker runtimes (SCION today, swappable tomorrow).

    Contract for a *verified* (non fire-and-forget) dispatch:
      1. ``preflight(project_dir)``      -> runtime (e.g. podman/docker) reachable?
      2. ``spawn(...)``                  -> provider accepted the launch request?
      3. ``wait_until_running(...)``     -> the worker pod actually exists and reports running?
    Only after step 3 succeeds should the orchestrator claim the ticket.
    """

    provider_name: str = "abstract"
    last_error: str = ""

    @abstractmethod
    def preflight(self, project_dir: str) -> ProviderResult:
        """Cheap health check of the provider runtime for a project (no mutations)."""

    @abstractmethod
    def spawn(
        self,
        project_dir: str,
        worker_id: str,
        prompt: str,
        branch: str,
        env: dict[str, str],
    ) -> bool:
        """Create and start a new worker with 1:1 ID == ticket_id in project_dir."""

    @abstractmethod
    def health(self, project_dir: str, worker_id: str) -> WorkerStatus | None:
        """Return the live status of one worker, or None if the provider knows nothing about it."""

    @abstractmethod
    def pause(self, project_dir: str, worker_id: str) -> bool:
        """Suspend/pause the worker while preserving its workspace state."""

    @abstractmethod
    def wake_with_message(self, project_dir: str, worker_id: str, message: str) -> bool:
        """Wake a paused worker and deliver review feedback."""

    @abstractmethod
    def attach_command(self, project_dir: str, worker_id: str) -> list[str]:
        """Return the interactive CLI command to attach the user's terminal to the worker."""

    @abstractmethod
    def delete(
        self,
        project_dir: str,
        worker_id: str,
        preserve_branch: bool = True,
    ) -> bool:
        """Permanently delete a paused worker pod after retention expiry."""

    @abstractmethod
    def list_workers(self, project_dir: str) -> dict[str, WorkerStatus]:
        """Return active and paused workers for a project keyed by worker_id."""

    @abstractmethod
    def logs(self, project_dir: str, worker_id: str) -> str:
        """Fetch recent logs from the worker runtime."""

    # ------------------------------------------------------------ optional hooks

    def workspace_path(self, project_dir: str, worker_id: str) -> Path | None:
        """Return the worker's *isolated* checkout on the host, if the runtime gives it one.

        ``None`` means the worker operates directly on ``project_dir`` (shared checkout).
        When a path is returned, the task force mirrors the ticket file into it after spawn and
        merges the worker's edits (notes, review tag) back into the project's ``.tickets/``.
        """
        return None

    def ensure_project_registered(self, project_dir: str) -> ProviderResult:
        """Register ``project_dir`` with the runtime's control plane once (e.g. link it to a Hub).

        Called explicitly by ``init``/``start`` only — never by dispatch — so exactly one
        runtime project exists per registered folder. Default: nothing to do.
        """
        return ProviderResult(ok=True, message="no project registration required")

    def post_spawn(self, project_dir: str, worker_id: str, timeout_seconds: float = 40.0) -> str:
        """Best-effort hook after a verified spawn (e.g. dismiss interactive harness prompts).

        Returns a short human-readable note for the logs (empty string if nothing was done).
        Must never raise.
        """
        return ""

    def wait_until_running(
        self,
        project_dir: str,
        worker_id: str,
        timeout_seconds: float = 30.0,
        poll_seconds: float = 2.0,
    ) -> WorkerStatus | None:
        """Poll ``health`` until the worker reports running (or timeout). Returns final status."""
        deadline = time.monotonic() + max(0.0, float(timeout_seconds))
        last: WorkerStatus | None = None
        while True:
            last = self.health(project_dir, worker_id)
            if last is not None and last.is_running:
                return last
            if last is not None and last.state == "error":
                return last
            if time.monotonic() >= deadline:
                return last
            time.sleep(max(0.1, float(poll_seconds)))


def get_provider(config: dict[str, Any], dry_run: bool = False) -> WorkerProvider:
    from tk_scion_taskforce.providers.scion import ScionProvider

    driver = str(config.get("provider", {}).get("driver", "scion")).lower()
    if driver in ("scion", "mock"):
        return ScionProvider(config, dry_run=(dry_run or driver == "mock"))
    raise ValueError(
        f"Unsupported provider.driver: {driver!r}. Supported drivers: 'scion', 'mock'."
    )
