"""OpenTelemetry local JSONL trace/metric emitter and 30-day rotating log manager."""

from __future__ import annotations

import gzip
import json
import os
import re
import secrets
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tk_scion_taskforce import __version__

ROTATED_DATE_RE = re.compile(r"\.(\d{4}-\d{2}-\d{2})(?:\.\d+)?(?:\.gz)?$")
TRACES_FILE = "otel-traces.jsonl"
METRICS_FILE = "otel-metrics.jsonl"
LOG_FILE = "taskforce.log"
WORKER_LOGS_DIR = "workers"
_RESOURCE = {"service.name": "tk-scion-taskforce", "service.version": __version__}


def project_slug(project_dir: Path) -> str:
    resolved = Path(project_dir).expanduser().resolve()
    safe = re.sub(r"[^A-Za-z0-9._-]+", "-", resolved.name).strip("-")
    return safe or "project"


def new_trace_id() -> str:
    return secrets.token_hex(16)


def new_span_id() -> str:
    return secrets.token_hex(8)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class TelemetryManager:
    """Manages local OpenTelemetry traces, metrics, task force logs, and 30-day log rotation.

    Failure policy ``warn`` (coder-soul §4.3): a failed write prints one warning to stderr and is
    dropped. Telemetry never raises into the worker lifecycle, so a full disk cannot orphan a pod.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        tel_cfg = config.get("telemetry", {})
        self.enabled: bool = bool(tel_cfg.get("enabled", True))

        env_log_dir = os.environ.get("TK_SCION_TASKFORCE_LOG_DIR")
        raw_log_dir = env_log_dir or tel_cfg.get(
            "log_dir", "~/.local/state/tk/scion-taskforce/logs"
        )
        self.log_dir = Path(raw_log_dir).expanduser().resolve()
        self.project_log_symlink: bool = bool(tel_cfg.get("project_log_symlink", True))

        self.traces_file = self.log_dir / TRACES_FILE
        self.metrics_file = self.log_dir / METRICS_FILE
        self.log_file = self.log_dir / LOG_FILE
        self.workers_dir = self.log_dir / WORKER_LOGS_DIR

        rot_cfg = tel_cfg.get("rotation", {})
        self.rotation_enabled: bool = bool(rot_cfg.get("enabled", True))
        self.max_bytes: int = int(rot_cfg.get("max_bytes", 104857600))
        self.retention_days: int = int(rot_cfg.get("retention_days", 30))
        self.compress: bool = bool(rot_cfg.get("compress", True))
        self._warned = False

    def _warn(self, exc: OSError) -> None:
        if not self._warned:
            print(f"tk-scion-taskforce: warning: telemetry write failed, continuing without it: {exc}", file=sys.stderr)
            self._warned = True

    def _append(self, path: Path, text: str) -> None:
        """Rotate if due, then append ``text`` to ``path``. Never raises (warn policy)."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._maybe_rotate_file(path)
            with open(path, "a", encoding="utf-8") as f:
                f.write(text)
        except OSError as exc:
            self._warn(exc)

    def ensure_project_symlink(self, project_dir: Path) -> None:
        if not self.project_log_symlink:
            return
        tickets_dir = Path(project_dir).expanduser().resolve() / ".tickets"
        if not tickets_dir.exists():
            return
        link_path = tickets_dir / ".scion-taskforce-logs"
        if link_path.exists() or link_path.is_symlink():
            return
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            link_path.symlink_to(self.log_dir)
        except OSError:
            pass

    def _worker_file(self, project_dir: Path, ticket_id: str, suffix: str) -> Path:
        safe_id = re.sub(r"[^A-Za-z0-9._-]+", "_", ticket_id)
        return (self.workers_dir / project_slug(project_dir)).resolve() / f"{safe_id}{suffix}"

    def worker_log_path(self, project_dir: Path, ticket_id: str) -> Path:
        return self._worker_file(project_dir, ticket_id, ".log")

    def save_worker_file(self, project_dir: Path, ticket_id: str, suffix: str, content: str) -> Path | None:
        """Write a per-worker file next to its log (brief, launch config). ``None`` if the write failed."""
        path = self._worker_file(project_dir, ticket_id, suffix)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        except OSError as exc:
            self._warn(exc)
            return None
        return path

    def save_worker_brief(self, project_dir: Path, ticket_id: str, brief_content: str) -> None:
        self.save_worker_file(project_dir, ticket_id, ".brief.md", brief_content)

    def read_worker_brief(self, project_dir: Path, ticket_id: str) -> str | None:
        try:
            return self._worker_file(project_dir, ticket_id, ".brief.md").read_text(encoding="utf-8")
        except OSError:
            return None

    def _maybe_rotate_file(self, file_path: Path) -> None:
        if not self.rotation_enabled or not file_path.exists():
            return
        try:
            stat = file_path.stat()
        except OSError:
            return
        if stat.st_size == 0:
            return

        now_utc = datetime.now(timezone.utc)
        mtime_utc = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

        should_rotate = False
        date_suffix = mtime_utc.strftime("%Y-%m-%d")
        if mtime_utc.date() < now_utc.date():  # daily rotation at UTC midnight
            should_rotate = True
        elif self.max_bytes > 0 and stat.st_size >= self.max_bytes:
            should_rotate = True
            date_suffix = now_utc.strftime("%Y-%m-%d")

        if not should_rotate:
            return

        self.rotate_file(file_path, date_suffix=date_suffix)

    def rotate_file(self, file_path: Path, date_suffix: str | None = None) -> Path | None:
        if not file_path.exists() or file_path.stat().st_size == 0:
            return None
        suffix_date = date_suffix or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        ext = ".gz" if self.compress else ""
        candidate = file_path.with_name(f"{file_path.name}.{suffix_date}{ext}")
        counter = 1
        while candidate.exists():
            candidate = file_path.with_name(f"{file_path.name}.{suffix_date}.{counter}{ext}")
            counter += 1

        if self.compress:
            with open(file_path, "rb") as f_in, gzip.open(candidate, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            file_path.write_text("", encoding="utf-8")
        else:
            shutil.move(str(file_path), str(candidate))
            file_path.touch()
        return candidate

    def purge_expired_logs(self, retention_days: int | None = None) -> int:
        """Delete rotated log archives older than retention_days (default 30 days)."""
        days = self.retention_days if retention_days is None else int(retention_days)
        cutoff_ts = time.time() - (days * 86400)
        purged = 0

        if not self.log_dir.exists():
            return 0

        for root, _, files in os.walk(self.log_dir):
            root_path = Path(root)
            for fname in files:
                match = ROTATED_DATE_RE.search(fname)
                if not match and not fname.endswith(".gz"):
                    continue
                fpath = root_path / fname
                is_expired = False
                try:
                    if fpath.stat().st_mtime < cutoff_ts:
                        is_expired = True
                except OSError:
                    continue

                if not is_expired and match:
                    try:
                        file_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(
                            tzinfo=timezone.utc
                        )
                        if file_date.timestamp() < cutoff_ts:
                            is_expired = True
                    except ValueError:
                        pass

                if is_expired:
                    try:
                        fpath.unlink()
                        purged += 1
                    except OSError:
                        pass

        if purged > 0:
            self.emit_metric("taskforce.logs.rotated_purged", purged, unit="files")
        return purged

    def log_event(
        self,
        level: str,
        message: str,
        trace_id: str | None = None,
        span_id: str | None = None,
        **extra: Any,
    ) -> None:
        record: dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "severity": level.upper(),
            "message": message,
            "service.name": "tk-scion-taskforce",
        }
        if trace_id:
            record["trace_id"] = trace_id
        if span_id:
            record["span_id"] = span_id
        if extra:
            record["attributes"] = extra
        self._append(self.log_file, json.dumps(record) + "\n")

    def log_worker(
        self,
        project_dir: Path,
        ticket_id: str,
        line: str,
        trace_id: str | None = None,
    ) -> None:
        prefix = f"[{utc_now_iso()}]"
        if trace_id:
            prefix += f" [trace_id={trace_id}]"
        lines = line.rstrip("\n").splitlines() or [""]
        self._append(self.worker_log_path(project_dir, ticket_id), "".join(f"{prefix} {sub}\n" for sub in lines))

    def emit_span(
        self,
        name: str,
        trace_id: str,
        span_id: str | None = None,
        parent_span_id: str | None = None,
        status_code: str = "OK",
        attributes: dict[str, Any] | None = None,
        events: list[dict[str, Any]] | None = None,
    ) -> str:
        actual_span_id = span_id or new_span_id()
        if not self.enabled:
            return actual_span_id
        span_record: dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "trace_id": trace_id,
            "span_id": actual_span_id,
            "parent_span_id": parent_span_id,
            "name": name,
            "kind": "INTERNAL",
            "status": {"code": status_code},
            "resource": _RESOURCE,
            "attributes": attributes or {},
            "events": events or [],
        }
        self._append(self.traces_file, json.dumps(span_record) + "\n")
        return actual_span_id

    def emit_metric(
        self,
        name: str,
        value: float,
        unit: str = "1",
        attributes: dict[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        metric_record: dict[str, Any] = {
            "timestamp": utc_now_iso(),
            "name": name,
            "value": value,
            "unit": unit,
            "resource": _RESOURCE,
            "attributes": attributes or {},
        }
        self._append(self.metrics_file, json.dumps(metric_record) + "\n")

    @staticmethod
    def _iter_file_lines_with_archives(active_file: Path) -> list[str]:
        parent = active_file.parent
        if not parent.exists():
            return []
        prefix = active_file.name + "."
        archives = sorted(
            p for p in parent.iterdir() if p.name.startswith(prefix) and p != active_file
        )
        lines: list[str] = []
        for arch in archives:
            try:
                if arch.name.endswith(".gz"):
                    with gzip.open(arch, "rt", encoding="utf-8", errors="replace") as gz:
                        lines.extend(gz.read().splitlines())
                else:
                    lines.extend(arch.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
        if active_file.exists():
            try:
                lines.extend(
                    active_file.read_text(encoding="utf-8", errors="replace").splitlines()
                )
            except OSError:
                pass
        return lines

    def read_spans(self, ticket_id: str | None = None) -> list[dict[str, Any]]:
        raw_lines = self._iter_file_lines_with_archives(self.traces_file)
        spans: list[dict[str, Any]] = []
        for raw in raw_lines:
            if not raw.strip():
                continue
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if ticket_id:
                attrs = item.get("attributes", {})
                if attrs.get("ticket.id") != ticket_id and attrs.get("worker.id") != ticket_id:
                    continue
            spans.append(item)
        return spans

    def read_logs(self, limit: int = 100) -> list[str]:
        lines = self._iter_file_lines_with_archives(self.log_file)
        return lines[-limit:] if limit > 0 else lines

    def read_worker_logs(
        self,
        project_dir: Path,
        ticket_id: str,
        limit: int = 200,
    ) -> list[str]:
        w_path = self.worker_log_path(project_dir, ticket_id)
        lines = self._iter_file_lines_with_archives(w_path)
        return lines[-limit:] if limit > 0 else lines
