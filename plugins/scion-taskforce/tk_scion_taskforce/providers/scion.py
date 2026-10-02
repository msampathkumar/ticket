"""SCION CLI implementation of the WorkerProvider interface."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from tk_scion_taskforce.providers import ProviderResult, WorkerProvider, WorkerStatus
from tk_scion_taskforce.tickets import validate_ticket_id

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


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


class ScionProvider(WorkerProvider):
    """Concrete WorkerProvider wrapping the SCION CLI ('scion --project <dir> ...')."""

    provider_name: str = "scion"

    def __init__(self, config: dict[str, Any], dry_run: bool = False) -> None:
        self.config = config
        prov_cfg = config.get("provider", {})
        self.binary_name = str(prov_cfg.get("binary", "scion") or "scion")
        self.profile = str(prov_cfg.get("profile", "") or "")
        self.harness_config = str(prov_cfg.get("harness_config", "") or "")
        self.branch_prefix = str(prov_cfg.get("branch_prefix", "") or "")
        self.extra_start_args = [str(x) for x in (prov_cfg.get("extra_start_args") or [])]
        self.extra_resume_args = [str(x) for x in (prov_cfg.get("extra_resume_args") or [])]
        self.auto_accept_prompts = bool(prov_cfg.get("auto_accept_prompts", True))
        self.prompt_patterns = [
            str(x) for x in (prov_cfg.get("auto_accept_prompt_patterns") or ["Yes, I trust this folder"])
        ]
        self.ready_patterns = [
            str(x)
            for x in (prov_cfg.get("harness_ready_patterns") or ["bypass permissions on", "esc to interrupt"])
        ]
        self.container_user = str(prov_cfg.get("container_user", "scion") or "scion")
        self.tmux_session = str(prov_cfg.get("tmux_session", "scion") or "scion")
        env_dry = os.environ.get("TK_SCION_TASKFORCE_DRY_RUN", "").lower() in (
            "1",
            "true",
            "yes",
        )
        self.dry_run = dry_run or env_dry
        self.last_commands: list[list[str]] = []
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
        self.last_commands.append(args)
        if self.dry_run:
            return subprocess.CompletedProcess(args=args, returncode=0, stdout="[dry-run] ok\n", stderr="")

        env = os.environ.copy()
        if extra_env:
            for k, v in extra_env.items():
                env[str(k)] = str(v)

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
        res = self._run([binary, "--project", proj, "list", "--format", "json"], cwd=proj, timeout=60)
        if res.returncode != 0:
            return ProviderResult(ok=False, message=self.last_error)
        return ProviderResult(ok=True, message="ok")

    def health(self, project_dir: str, worker_id: str) -> WorkerStatus | None:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        if self.dry_run:
            state = self._dry_run_pods.get(clean_id)
            if state is None:
                return None
            return WorkerStatus(worker_id=clean_id, project_dir=proj, state=state)
        workers = self.list_workers(proj)
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
        target_branch = branch or self.format_branch(clean_id)

        cmd: list[str] = [
            binary,
            "--project",
            proj,
            "start",
            clean_id,
            prompt,
            "--branch",
            target_branch,
            "--enable-telemetry",
            "--non-interactive",
        ]
        if self.profile:
            cmd.extend(["--profile", self.profile])
        if self.harness_config:
            cmd.extend(["--harness-config", self.harness_config])
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

        res = self._run([binary, "--project", proj, "suspend", clean_id], cwd=proj)
        if res.returncode != 0:
            res = self._run([binary, "--project", proj, "stop", clean_id], cwd=proj)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods[clean_id] = "paused"
        return res.returncode == 0

    def wake_with_message(self, project_dir: str, worker_id: str, message: str) -> bool:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

        res = self._run([binary, "--project", proj, "message", clean_id, message, "--wake"], cwd=proj)
        if res.returncode != 0:
            fallback = [binary, "--project", proj, "resume", clean_id, message, "--enable-telemetry"]
            fallback.extend(self.extra_resume_args)
            res = self._run(fallback, cwd=proj)
        if res.returncode == 0 and self.dry_run:
            self._dry_run_pods[clean_id] = "running"
        return res.returncode == 0

    def attach_command(self, project_dir: str, worker_id: str) -> list[str]:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()

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

    def list_workers(self, project_dir: str) -> dict[str, WorkerStatus]:
        proj = self._validate_project_dir(project_dir)
        if self.dry_run:
            return {
                wid: WorkerStatus(worker_id=wid, project_dir=proj, state=st)
                for wid, st in self._dry_run_pods.items()
            }
        binary = self._resolve_binary()
        res = self._run([binary, "--project", proj, "list", "--format", "json"], cwd=proj, timeout=60)
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
            workers[wid] = WorkerStatus(
                worker_id=wid,
                project_dir=proj,
                state=_normalize_state(raw_status),
                branch=item.get("branch"),
            )
        return workers

    # ---------------------------------------------------------- optional hooks

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

    def _container_for(self, project_dir: str, worker_id: str) -> tuple[str, str] | None:
        """Return (runtime, container_id) for a worker from ``scion list --format json``."""
        proj = self._validate_project_dir(project_dir)
        binary = self._resolve_binary()
        res = self._run([binary, "--project", proj, "list", "--format", "json"], cwd=proj, timeout=60)
        if res.returncode != 0 or not res.stdout.strip():
            return None
        try:
            items = json.loads(res.stdout)
        except json.JSONDecodeError:
            return None
        wanted = worker_id.lower()
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict) or str(item.get("name", "")).lower() != wanted:
                continue
            cid = str(item.get("containerId") or "").strip()
            runtime = str(item.get("runtime") or "podman").strip() or "podman"
            if cid:
                return runtime, cid
        return None

    def _pane(self, runtime: str, cid: str) -> str:
        res = self._run(
            [runtime, "exec", "-u", self.container_user, cid, "tmux", "capture-pane", "-p",
             "-t", self.tmux_session, "-S", "-40"],
            cwd=os.getcwd(), timeout=20,
        )
        return res.stdout if res.returncode == 0 else ""

    def post_spawn(self, project_dir: str, worker_id: str, timeout_seconds: float = 40.0) -> str:
        """Auto-accept interactive harness start-up prompts (e.g. Claude Code's folder-trust
        dialog, which scion fails to pre-seed for project-local workspaces) by pressing Enter
        in the agent's tmux session. Best effort; silent no-op when anything is unavailable."""
        if self.dry_run or not self.auto_accept_prompts:
            return ""
        try:
            clean_id = validate_ticket_id(worker_id)
            target = self._container_for(project_dir, clean_id)
            if target is None:
                return ""
            runtime, cid = target
            if not shutil.which(runtime):
                return ""
            deadline = time.monotonic() + max(0.0, float(timeout_seconds))
            accepted: list[str] = []
            while time.monotonic() < deadline:
                pane = self._pane(runtime, cid)
                hit = next((pat for pat in self.prompt_patterns if pat in pane), None)
                if hit is None:
                    if accepted or any(pat in pane for pat in self.ready_patterns):
                        break  # prompt handled/gone, or the harness is already at its main prompt
                    time.sleep(2.0)  # pane not up yet / no prompt (yet); keep polling
                    continue
                self._run(
                    [runtime, "exec", "-u", self.container_user, cid, "tmux", "send-keys",
                     "-t", self.tmux_session, "Enter"],
                    cwd=os.getcwd(), timeout=20,
                )
                accepted.append(hit)
                time.sleep(3.0)
            if accepted:
                return f"auto-accepted harness prompt(s): {', '.join(dict.fromkeys(accepted))}"
            return ""
        except Exception as exc:  # noqa: BLE001 - must never break dispatch
            self.last_error = f"post_spawn: {exc}"
            return ""

    def logs(self, project_dir: str, worker_id: str) -> str:
        clean_id = validate_ticket_id(worker_id)
        proj = self._validate_project_dir(project_dir)
        if self.dry_run:
            return f"[dry-run] logs for worker {clean_id} in {proj}"
        binary = self._resolve_binary()
        res = self._run([binary, "--project", proj, "logs", clean_id], cwd=proj)
        return res.stdout or res.stderr
