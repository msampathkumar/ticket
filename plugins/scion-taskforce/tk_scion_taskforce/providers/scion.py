"""Thin adapter around the Scion CLI (``scion --project <dir> ...``): the only worker runtime."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tk_scion_taskforce.tickets import validate_ticket_id
from tk_scion_taskforce.wizard import resolve_model_alias

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


@dataclass
class WorkerStatus:
    worker_id: str      # 1:1 with ticket_id (e.g. "tic-a1b2")
    project_dir: str    # Project root path
    state: str          # "running" | "paused" | "stopped" | "error" | "unknown"

    @property
    def is_running(self) -> bool:
        return self.state == "running"


@dataclass
class ProviderResult:
    ok: bool
    message: str = ""


def _hint_for(detail: str, project_dir: str) -> str:
    """Turn well-known scion failures into one actionable sentence for `status`/logs."""
    low = detail.lower()
    if "must be in .gitignore" in low or "run 'scion init'" in low:
        return f" → HINT: run `scion init` once inside {project_dir} (it adds agents/ to .gitignore), then retry."
    if "podman" in low and ("failed" in low or "cannot connect" in low or "exit status 125" in low):
        return " → HINT: the container runtime is down; start it (`podman machine start`) and retry."
    if "no such file" in low and "scion" in low or "not found" in low and "binary" in low:
        return " → HINT: install the scion CLI or set provider.binary in scion-taskforce.yaml."
    return ""


def _normalize_state(raw: str) -> str:
    raw = (raw or "unknown").lower()
    if "error" in raw or "fail" in raw:
        return "error"
    if "run" in raw or "thinking" in raw or "waiting_for_input" in raw or "idle" in raw:
        return "running"
    if any(k in raw for k in ("suspend", "pause", "stop")):
        return "paused"
    return raw


def apply_vertex_env(prov_cfg: dict[str, Any], env: dict[str, str]) -> dict[str, str]:
    """Set Vertex AI project/location in ``env`` for `scion start`.

    `provider.gcp_project` / `provider.gcp_region` (written by `init`) win over the shell;
    without them, keep the shell's values or fall back to a region the harness supports.
    """
    project = str(prov_cfg.get("gcp_project", "") or "").strip()
    if project:
        env["GOOGLE_CLOUD_PROJECT"] = project
    region = str(prov_cfg.get("gcp_region", "") or "").strip()
    if not region and "GOOGLE_CLOUD_REGION" in env:
        return env
    if not region:
        harness = str(prov_cfg.get("harness_config", "") or "")
        region = env.get("GOOGLE_CLOUD_LOCATION") or env.get("VERTEX_LOCATION") or (
            "us-east5" if harness == "claude" else "us-central1"
        )
    env["GOOGLE_CLOUD_REGION"] = region
    env["GOOGLE_CLOUD_LOCATION"] = region
    return env


class ScionProvider:
    """Runs Scion CLI commands for one config. ``dry_run`` (or ``TK_SCION_TASKFORCE_DRY_RUN=1``)
    simulates every command in-process; the test suite relies on it."""

    def __init__(self, config: dict[str, Any], dry_run: bool = False) -> None:
        self.config = config
        prov_cfg = config.get("provider", {})
        self.binary_name = str(prov_cfg.get("binary", "scion") or "scion")
        self.profile = str(prov_cfg.get("profile", "") or "")
        self.template = str(prov_cfg.get("template", "") or "")
        self.harness_config = str(prov_cfg.get("harness_config", "") or "")
        self.model = str(prov_cfg.get("model", "") or "")
        self.branch_prefix = str(prov_cfg.get("branch_prefix", "") or "")
        self.extra_start_args = [str(x) for x in (prov_cfg.get("extra_start_args") or [])]
        self.extra_resume_args = [str(x) for x in (prov_cfg.get("extra_resume_args") or [])]
        env_dry = os.environ.get("TK_SCION_TASKFORCE_DRY_RUN", "").lower() in ("1", "true", "yes")
        self.dry_run = dry_run or env_dry
        self.last_error = ""
        # Dry-run only: simulate pods spawned in this process so verification succeeds.
        self._dry_run_pods: dict[str, str] = {}

    def _resolve_binary(self) -> str:
        if os.path.isabs(self.binary_name):
            resolved = Path(self.binary_name).resolve()
            if resolved.is_file() and os.access(resolved, os.X_OK):
                return str(resolved)
        found = shutil.which(self.binary_name)
        if found:
            return found
        return self.binary_name

    def _validate_project_dir(self, project_dir: str) -> str:
        resolved = Path(project_dir).expanduser().resolve()
        if not resolved.is_dir():
            raise ValueError(f"Project directory does not exist: {project_dir!r}")
        return str(resolved)

    def _run(
        self,
        args: list[str],
        cwd: str,
        extra_env: dict[str, str] | None = None,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess[str]:
        self.last_error = ""
        if self.dry_run:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[dry-run] ok\n", stderr="")

        env = os.environ.copy()
        if extra_env:
            for k, v in extra_env.items():
                env[str(k)] = str(v)
        apply_vertex_env(self.config.get("provider", {}), env)

        try:
            res = subprocess.run(
                args,
                cwd=cwd,
                env=env,
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            res = subprocess.CompletedProcess(
                args=args, returncode=127, stdout="", stderr=f"Provider binary not found: {exc}"
            )
        except subprocess.TimeoutExpired as exc:
            res = subprocess.CompletedProcess(
                args=args, returncode=124, stdout="", stderr=f"Provider command timed out: {exc}"
            )
        if res.returncode != 0:
            detail = _ANSI_RE.sub("", (res.stderr or res.stdout or "")).strip()
            # Drop the usage dump cobra appends after the real error.
            detail = detail.split("\nUsage:", 1)[0].strip()
            self.last_error = (
                f"{Path(args[0]).name} {args[3] if len(args) > 3 else ''} exited {res.returncode}: {detail}"
                + _hint_for(detail, cwd)
            )
        return res

    def format_branch(self, worker_id: str) -> str:
        clean_id = validate_ticket_id(worker_id)
        if self.branch_prefix:
            return f"{self.branch_prefix.rstrip('/')}/{clean_id}"
        return clean_id

    # ------------------------------------------------------------------ health

    def preflight(self, project_dir: str) -> ProviderResult:
        proj = self._validate_project_dir(project_dir)
        if self.dry_run:
            return ProviderResult(ok=True, message="[dry-run] provider assumed healthy")
        binary = self._resolve_binary()

        res = self._run(
            [binary, "--project", proj, "list", "--format", "json", "--non-interactive"],
            cwd=proj,
            timeout=60,
        )
        if res.returncode != 0:
            return ProviderResult(ok=False, message=self.last_error)

        # Dispatch must never create a Hub project (that is `init`'s job): refuse an unlinked folder.
        if self._hub_unlinked(self._hub_status(binary, proj)):
            return ProviderResult(
                ok=False,
                message=(
                    f"project {proj} is not linked to the Scion Hub"
                    f" → HINT: run `tk scion-taskforce init` in {proj} once to link it, then retry."
                ),
            )

        return ProviderResult(ok=True, message="ok")

    def _hub_status(self, binary: str, proj: str) -> str | None:
        """Read-only `scion hub status` output, or ``None`` if the command failed."""
        try:
            res = self._run(
                [binary, "--project", proj, "hub", "status", "--non-interactive"],
                cwd=proj,
                timeout=15,
            )
        except Exception:  # noqa: BLE001 - status probe is best effort
            return None
        if res.returncode != 0:
            return None
        return _ANSI_RE.sub("", res.stdout or "")

    @staticmethod
    def _hub_unlinked(status: str | None) -> bool:
        """True only when the Hub is reachable and this folder is not linked to it."""
        return bool(status) and "Connection: ok" in status and "Linked: no" in status

    def ensure_project_registered(self, project_dir: str) -> ProviderResult:
        """Link ``project_dir`` to the Scion Hub once: one Hub project per project folder.

        No-op when already linked or when the Hub is unreachable (local mode).
        """
        proj = self._validate_project_dir(project_dir)
        if self.dry_run:
            return ProviderResult(ok=True, message="[dry-run] Hub link skipped")
        binary = self._resolve_binary()
        status = self._hub_status(binary, proj)
        if not status or "Connection: ok" not in status:
            return ProviderResult(ok=True, message="Hub not reachable; project runs in local mode")
        if "Linked: no" not in status:
            return ProviderResult(ok=True, message="project already linked to the Scion Hub")
        link = self._run(
            [binary, "--project", proj, "hub", "link", "--yes", "--non-interactive"],
            cwd=proj,
            timeout=30,
        )
        if link.returncode != 0:
            return ProviderResult(ok=False, message=f"Hub link failed: {self.last_error}")
        self._run([binary, "--project", proj, "hub", "enable", "--non-interactive"], cwd=proj, timeout=15)
        return ProviderResult(ok=True, message="project linked to the Scion Hub")

    def health(self, project_dir: str, worker_id: str) -> WorkerStatus | None:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        if self.dry_run:
            state = self._dry_run_pods.get(clean_id)
            if state is None:
                return None
            return WorkerStatus(worker_id=clean_id, project_dir=proj, state=state)
        workers = self._list_agents(proj)
        # scion normalises agent names to lower-case (``AO-08gp`` -> ``ao-08gp``),
        # so match case-insensitively to avoid false "pod never appeared" results.
        if clean_id in workers:
            return workers[clean_id]
        wanted = clean_id.lower()
        for name, status in workers.items():
            if name.lower() == wanted:
                return status
        return None

    # --------------------------------------------------------------- lifecycle

    def spawn(
        self,
        project_dir: str,
        worker_id: str,
        prompt: str,
        branch: str,
        env: dict[str, str],
    ) -> bool:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

        cmd: list[str] = [
            binary,
            "--project",
            proj,
            "start",
            clean_id,
            prompt,
            "--branch",
            branch,
            "-w",
            proj,
            "--enable-telemetry",
            "--non-interactive",
        ]
        if self.template and (Path(proj) / ".scion" / "templates" / self.template).is_dir():
            cmd.extend(["-t", self.template])
        if self.profile:
            cmd.extend(["--profile", self.profile])
        if self.harness_config:
            cmd.extend(["--harness-config", self.harness_config])
        if self.model and self.model.lower() not in ("default", ""):
            cmd.extend(["--model", resolve_model_alias(self.harness_config, self.model)])
        if self.extra_start_args:
            cmd.extend(self.extra_start_args)

        res = self._run(cmd, cwd=proj, extra_env=env)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods[clean_id] = "running"
        return res.returncode == 0

    def pause(self, project_dir: str, worker_id: str) -> bool:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

        res = self._run([binary, "--project", proj, "suspend", clean_id, "--non-interactive"], cwd=proj)
        if res.returncode != 0:
            res = self._run([binary, "--project", proj, "stop", clean_id, "--non-interactive"], cwd=proj)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods[clean_id] = "paused"
        return res.returncode == 0

    def stop(self, project_dir: str, worker_id: str) -> bool:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        res = self._run([self._resolve_binary(), "--project", proj, "stop", clean_id, "--non-interactive"], cwd=proj)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods[clean_id] = "stopped"
        return res.returncode == 0

    def wake_with_message(self, project_dir: str, worker_id: str, message: str) -> bool:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

        res = self._run(
            [binary, "--project", proj, "message", clean_id, message, "--wake", "--non-interactive"],
            cwd=proj,
        )
        if res.returncode != 0:
            fallback = [
                binary,
                "--project",
                proj,
                "resume",
                clean_id,
                message,
                "--enable-telemetry",
                "--non-interactive",
            ]
            fallback.extend(self.extra_resume_args)
            res = self._run(fallback, cwd=proj)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods[clean_id] = "running"
        return res.returncode == 0

    def attach_command(self, project_dir: str, worker_id: str) -> list[str]:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

        live = self.health(proj, clean_id)
        if live is not None and live.is_running:
            return [binary, "--project", proj, "attach", clean_id]
        cmd = [binary, "--project", proj, "resume", clean_id, "--enable-telemetry", "--attach"]
        cmd.extend(self.extra_resume_args)
        return cmd

    def delete(
        self,
        project_dir: str,
        worker_id: str,
        preserve_branch: bool = True,
    ) -> bool:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

        cmd = [binary, "--project", proj, "delete", clean_id, "--non-interactive"]
        if preserve_branch:
            cmd.append("--preserve-branch")
        res = self._run(cmd, cwd=proj)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods.pop(clean_id, None)
        return res.returncode == 0

    def wait_until_running(
        self, project_dir: str, worker_id: str, timeout_seconds: float = 30.0, poll_seconds: float = 2.0
    ) -> WorkerStatus | None:
        """Poll ``health`` until the worker reports running or error, or the timeout passes."""
        deadline = time.monotonic() + max(0.0, float(timeout_seconds))
        while True:
            last = self.health(project_dir, worker_id)
            if last is not None and last.state in ("running", "error"):
                return last
            if time.monotonic() >= deadline:
                return last
            time.sleep(max(0.1, float(poll_seconds)))

    def _list_agents(self, proj: str) -> dict[str, WorkerStatus]:
        res = self._run(
            [self._resolve_binary(), "--non-interactive", "--project", proj, "list", "--format", "json"],
            cwd=proj,
            timeout=60,
        )
        workers: dict[str, WorkerStatus] = {}
        if res.returncode != 0 or not res.stdout.strip():
            return workers
        try:
            payload = json.loads(res.stdout)
        except json.JSONDecodeError:
            return workers
        items = payload if isinstance(payload, list) else payload.get("agents", payload.get("items", []))
        for item in items or []:
            if not isinstance(item, dict):
                continue
            wid = str(item.get("name") or item.get("id") or "").strip()
            if not wid:
                continue
            raw_status = str(item.get("phase") or item.get("status") or item.get("state") or "unknown")
            workers[wid] = WorkerStatus(worker_id=wid, project_dir=proj, state=_normalize_state(raw_status))
        return workers

    def workspace_path(self, project_dir: str, worker_id: str) -> Path | None:
        """Project-local scion projects (``scion init``) give each agent a git worktree at
        ``<project>/.scion/agents/<id>/workspace``. Hub/external projects mount the shared
        checkout instead, in which case this returns ``None``."""
        clean_id = validate_ticket_id(worker_id)
        proj = Path(self._validate_project_dir(project_dir))
        for name in (clean_id, clean_id.lower()):
            candidate = proj / ".scion" / "agents" / name / "workspace"
            if candidate.is_dir():
                return candidate
        return None
