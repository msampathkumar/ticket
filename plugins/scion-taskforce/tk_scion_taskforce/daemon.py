"""Multi-project reconciler loop, dispatcher, feedback relay, and GC for tk-scion-taskforce."""

from __future__ import annotations

import signal
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from tk_scion_taskforce.config import load_config
from tk_scion_taskforce.providers import WorkerProvider, get_provider
from tk_scion_taskforce.server import load_state, normalize_project_dir, save_state
from tk_scion_taskforce.telemetry import (
    TelemetryManager,
    new_span_id,
    new_trace_id,
    project_slug,
    utc_now_iso,
)
from tk_scion_taskforce.tickets import (
    TicketInfo,
    add_ticket_tag,
    append_ticket_note,
    get_ready_tickets,
    load_all_tickets,
    merge_worker_ticket_copy,
    parse_ticket_file,
    remove_ticket_tag,
    resolve_ticket_path,
    run_tk_show,
    update_ticket_frontmatter,
)


class DispatchError(Exception):
    """Raised when the provider runtime cannot launch a verified worker.

    Carries ``abort_project=True`` when the failure is environmental (runtime down,
    binary missing) and further spawns in the same project should be skipped this pass.
    """

    def __init__(self, message: str, abort_project: bool = True) -> None:
        super().__init__(message)
        self.abort_project = abort_project


def _worker_key(project_dir: str | Path, ticket_id: str) -> str:
    return f"{normalize_project_dir(project_dir)}::{ticket_id}"


def classify_work_type(ticket: TicketInfo, config: dict[str, Any]) -> str:
    """Return ``"review"`` for pull-request tickets, else ``"implement"``.

    PR tickets are recognised by tag (``worker.review_tags``, default ``pr``/``review``)
    or by ``external-ref`` prefix (``worker.review_ref_prefixes``, default ``gh-pr-``) —
    which is exactly what ``tk github sync --prs`` produces.
    """
    worker_cfg = config.get("worker", {}) or {}
    review_tags = {str(t).lower() for t in (worker_cfg.get("review_tags") or ["pr", "review"])}
    prefixes = [str(p).lower() for p in (worker_cfg.get("review_ref_prefixes") or ["gh-pr-"])]
    ticket_tags = {str(t).lower() for t in ticket.tags}
    if ticket_tags & review_tags:
        return "review"
    ref = (ticket.external_ref or "").lower()
    if ref and any(ref.startswith(p) for p in prefixes):
        return "review"
    return "implement"


def _pr_number_from_ref(external_ref: str) -> str:
    """``gh-pr-2246`` -> ``2246``; anything else -> ``""``."""
    ref = (external_ref or "").strip()
    tail = ref.rsplit("-", 1)[-1] if "-" in ref else ref
    return tail if tail.isdigit() else ""


def _reporting_protocol(ticket: TicketInfo, claim_tag: str, review_tag: str) -> str:
    rel_path = f".tickets/{ticket.path.name}"
    return (
        "### Reporting Back (mandatory — the orchestrator watches the ticket file)\n"
        f"The ticket lives at `{rel_path}` inside this workspace. `tk` may NOT be installed in this pod.\n"
        f"- If `tk` is available: `tk add-note {ticket.id} \"## Task Force Worker Report ...\"` then\n"
        f"  `tk update {ticket.id} --tags {claim_tag},{review_tag}`.\n"
        f"- Otherwise edit `{rel_path}` directly: append under a `## Notes` heading a block of the form\n"
        "  `**<UTC timestamp YYYY-MM-DDTHH:MM:SSZ>**` followed by a blank line and your report, and set the\n"
        f"  frontmatter to `tags: [{claim_tag}, {review_tag}]` while keeping `status: in_progress`.\n"
        "- Never set `status: closed` yourself; a human closes the ticket after review.\n"
        "- Commit your work on the branch; do NOT push, merge, rebase onto other branches, or `git stash`:\n"
        "  this checkout is shared with the human operator.\n"
        "- Then stop. The orchestrator pauses your pod and wakes you with any review feedback as a new note.\n"
    )


def _default_prompt(ticket: TicketInfo, branch: str, work_type: str, claim_tag: str, review_tag: str) -> str:
    ticket_details = run_tk_show(ticket.project_dir, ticket.id)
    header = (
        f"You are an autonomous SCION task force worker assigned to ticket `{ticket.id}` "
        f"in project `{ticket.project_dir}` (mounted here as your workspace).\n\n"
        f"### Ticket Details (`tk show {ticket.id}`)\n{ticket_details.strip()}\n\n"
    )
    if work_type == "review":
        pr_num = _pr_number_from_ref(ticket.external_ref)
        pr_hint = (
            f"`gh pr checkout {pr_num}` (or `git fetch origin pull/{pr_num}/head:{branch} && git checkout {branch}`)"
            if pr_num
            else "the branch referenced by the ticket"
        )
        task = (
            "### Your Job: Pull-Request Review\n"
            f"1. Fetch the PR under review with {pr_hint}. Do not modify the PR's commits.\n"
            "2. Review the full diff against the base branch: correctness, tests, security, API/spec "
            "compatibility, docs, and style consistent with this repository.\n"
            "3. Run the project's test/lint suite on the PR head if it exists (e.g. `make test`).\n"
            "4. Write a structured review report into the ticket (see Reporting Back): "
            "**Summary**, **Blocking issues**, **Suggestions**, **Verdict** (approve / request changes), "
            "each finding with `path:line`.\n"
            f"5. If `gh` is authenticated in this pod you MAY additionally post the same report as a PR comment "
            f"(`gh pr comment {pr_num or '<n>'} --body-file <report>`); never approve/merge via `gh`.\n\n"
        )
    else:
        task = (
            "### Your Job: Implementation\n"
            f"1. Implement the task described in ticket `{ticket.id}` on branch `{branch}` "
            "(create it from the current HEAD if it does not exist).\n"
            "2. Keep changes minimal and focused on the ticket; follow the repo's conventions and AGENTS/CLAUDE guides.\n"
            "3. Run the project test suite (e.g. `make test`) and lints; fix what you break.\n"
            "4. Commit on the branch with a clear message referencing the ticket id.\n"
            "5. Write a completion report into the ticket (see Reporting Back): "
            "**Summary of changes**, **Files touched**, **Verification results**, **Open questions**.\n\n"
        )
    return header + task + _reporting_protocol(ticket, claim_tag, review_tag)


def build_worker_prompt(
    ticket: TicketInfo,
    config: dict[str, Any],
    branch: str,
) -> str:
    tags_cfg = config.get("tags", {})
    claim_tag = str(tags_cfg.get("claim", "taskforce"))
    review_tag = str(tags_cfg.get("review", "waiting-for-review"))
    work_type = classify_work_type(ticket, config)

    # Optional user template (worker.prompt_file) with simple {placeholder} substitution.
    worker_cfg = config.get("worker", {}) or {}
    prompt_file = str(worker_cfg.get("prompt_file") or "").strip()
    if prompt_file:
        template_path = Path(prompt_file).expanduser()
        if not template_path.is_absolute():
            template_path = (ticket.project_dir / template_path).resolve()
        if template_path.is_file():
            template = template_path.read_text(encoding="utf-8")
            mapping = {
                "ticket_id": ticket.id,
                "ticket_title": ticket.title,
                "project_dir": str(ticket.project_dir),
                "branch": branch,
                "work_type": work_type,
                "claim_tag": claim_tag,
                "review_tag": review_tag,
                "external_ref": ticket.external_ref,
                "ticket_details": run_tk_show(ticket.project_dir, ticket.id).strip(),
            }
            for key, value in mapping.items():
                template = template.replace("{" + key + "}", str(value))
            return template

    return _default_prompt(ticket, branch, work_type, claim_tag, review_tag)


def _parse_iso_ts(ts_str: str | None) -> float | None:
    if not ts_str:
        return None
    cleaned = ts_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(cleaned).timestamp()
    except ValueError:
        return None


def is_eligible_for_dispatch(ticket: TicketInfo, config: dict[str, Any]) -> tuple[bool, str]:
    """Opt-in eligibility: user must have tagged the ticket with ``tags.claim``.

    Returns (eligible, reason).
    """
    tags_cfg = config.get("tags", {})
    claim_tag = str(tags_cfg.get("claim", "taskforce"))
    ignore_tag = str(tags_cfg.get("ignore", "no-taskforce"))
    review_tag = str(tags_cfg.get("review", "waiting-for-review"))

    if ticket.status != "open":
        return False, f"status is {ticket.status!r}, not 'open'"
    if ignore_tag in ticket.tags:
        return False, f"tagged {ignore_tag!r}"
    if review_tag in ticket.tags:
        return False, f"tagged {review_tag!r}"
    if claim_tag not in ticket.tags:
        return False, f"missing opt-in tag {claim_tag!r}"
    return True, "ok"


def _record_project_health(
    state: dict[str, Any],
    telemetry: TelemetryManager,
    proj_str: str,
    ok: bool,
    message: str,
) -> None:
    """Persist provider health per project and log only on transitions (avoid log spam)."""
    health: dict[str, dict[str, Any]] = state.setdefault("project_health", {})
    prev = health.get(proj_str, {})
    changed = prev.get("ok") is not ok
    health[proj_str] = {"ok": ok, "message": message, "checked_at": utc_now_iso()}
    if changed:
        telemetry.log_daemon(
            "INFO" if ok else "ERROR",
            (
                f"Provider runtime healthy for {proj_str}"
                if ok
                else f"Provider runtime UNAVAILABLE for {proj_str}; dispatch paused: {message}"
            ),
            project=proj_str,
        )
        telemetry.emit_metric(
            "taskforce.provider.healthy",
            1 if ok else 0,
            attributes={"project.path": proj_str},
        )
    save_state(state)


def dispatch_ticket(
    project_dir: Path,
    ticket: TicketInfo,
    config: dict[str, Any],
    telemetry: TelemetryManager,
    provider: WorkerProvider,
    state: dict[str, Any],
    skip_preflight: bool = False,
) -> bool:
    """Launch a worker for ``ticket`` and claim it ONLY after the pod is verified running.

    Raises ``DispatchError`` when the provider runtime is unavailable so callers can stop
    iterating over the remaining tickets in the same project for this pass.
    """
    tags_cfg = config.get("tags", {})
    claim_tag = str(tags_cfg.get("claim", "taskforce"))
    watcher_cfg = config.get("watcher", {})
    verify_timeout = float(watcher_cfg.get("spawn_verify_timeout_seconds", 30))
    prompt_timeout = float(watcher_cfg.get("spawn_prompt_unblock_seconds", 40))
    verify_poll = float(watcher_cfg.get("spawn_verify_poll_seconds", 2))

    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})

    trace_id = new_trace_id()
    lifecycle_span_id = new_span_id()
    branch_prefix = str(config.get("provider", {}).get("branch_prefix", "") or "")
    branch = f"{branch_prefix.rstrip('/')}/{ticket.id}" if branch_prefix else ticket.id
    slug = project_slug(project_dir)
    base_attrs = {
        "ticket.id": ticket.id,
        "project.path": proj_str,
        "project.name": slug,
        "worker.id": ticket.id,
        "worker.provider": provider.provider_name,
        "worker.branch": branch,
    }

    # 0. Pre-flight: is the provider runtime (podman/docker/k8s) reachable at all?
    if not skip_preflight:
        pre = provider.preflight(proj_str)
        _record_project_health(state, telemetry, proj_str, pre.ok, pre.message)
        if not pre.ok:
            raise DispatchError(f"provider preflight failed: {pre.message}", abort_project=True)

    # 1. Idempotency: adopt an already-running pod with this ID instead of double-spawning.
    existing = provider.health(proj_str, ticket.id)
    if existing is not None and existing.is_running:
        telemetry.log_daemon(
            "WARNING",
            f"Adopting pre-existing running worker {ticket.id} in {proj_str}",
            trace_id=trace_id,
            ticket_id=ticket.id,
        )
    elif existing is not None:
        # A dead pod left behind by a previous attempt (worker state 'error'/'deleted', or the
        # ticket was explicitly reopened by a human) is replaced; anything else is left alone.
        prev = state.get("workers", {}).get(wkey, {})
        retry_ok = prev.get("state") in ("error", "deleted") or not prev
        if retry_ok and provider.delete(proj_str, ticket.id, preserve_branch=True):
            telemetry.log_daemon(
                "WARNING",
                f"Replaced stale {existing.state!r} pod for {ticket.id} in {proj_str} before relaunch",
                trace_id=trace_id,
                ticket_id=ticket.id,
            )
            existing = None  # the slot is free now; fall through to a fresh spawn
        else:
            telemetry.log_daemon(
                "WARNING",
                f"Worker {ticket.id} already exists in state {existing.state!r}; "
                f"not spawning (use 'tk scion-taskforce attach {ticket.id}' or delete the pod)",
                trace_id=trace_id,
                ticket_id=ticket.id,
            )
            return False

    telemetry.ensure_project_symlink(project_dir)
    prompt = build_worker_prompt(ticket, config, branch=branch)
    worker_env = {
        "OTEL_EXPORTER_OTLP_TRACES_FILE": str(telemetry.traces_file),
        "OTEL_EXPORTER_OTLP_METRICS_FILE": str(telemetry.metrics_file),
        "OTEL_RESOURCE_ATTRIBUTES": (
            f"service.name=scion-worker,ticket.id={ticket.id},"
            f"worker.id={ticket.id},project.name={slug}"
        ),
        "TRACEPARENT": f"00-{trace_id}-{lifecycle_span_id}-01",
    }

    # 2. Spawn (request accepted by provider?)
    if existing is None:
        ok = provider.spawn(
            project_dir=proj_str,
            worker_id=ticket.id,
            prompt=prompt,
            branch=branch,
            env=worker_env,
        )
        if not ok:
            err = provider.last_error or "provider.spawn returned False"
            telemetry.emit_span(
                name="taskforce.worker.spawn",
                trace_id=trace_id,
                parent_span_id=lifecycle_span_id,
                status_code="ERROR",
                attributes={**base_attrs, "worker.state": "error", "error.message": err},
            )
            telemetry.log_daemon(
                "ERROR",
                f"Spawn FAILED for {ticket.id} in {proj_str}; ticket left untouched: {err}",
                trace_id=trace_id,
                ticket_id=ticket.id,
                project=proj_str,
            )
            telemetry.log_worker(project_dir, ticket.id, f"Spawn failed: {err}", trace_id=trace_id)
            telemetry.emit_metric("taskforce.workers.spawn_failed", 1, attributes={"project.name": slug})
            _record_project_health(state, telemetry, proj_str, False, err)
            raise DispatchError(err, abort_project=True)

    # 3. Verify the pod actually exists and is running (NOT fire-and-forget).
    status = provider.wait_until_running(
        proj_str, ticket.id, timeout_seconds=verify_timeout, poll_seconds=verify_poll
    )
    if status is None or not status.is_running:
        observed = status.state if status else "not_found"
        err = (
            f"worker {ticket.id} did not reach 'running' within {verify_timeout:.0f}s "
            f"(observed: {observed}). {provider.last_error}".strip()
        )
        telemetry.emit_span(
            name="taskforce.worker.spawn",
            trace_id=trace_id,
            parent_span_id=lifecycle_span_id,
            status_code="ERROR",
            attributes={**base_attrs, "worker.state": observed, "error.message": err},
        )
        telemetry.log_daemon(
            "ERROR",
            f"Spawn verification FAILED for {ticket.id} in {proj_str}; ticket left untouched: {err}",
            trace_id=trace_id,
            ticket_id=ticket.id,
            project=proj_str,
        )
        telemetry.log_worker(project_dir, ticket.id, f"Spawn verification failed: {err}", trace_id=trace_id)
        telemetry.emit_metric("taskforce.workers.spawn_unverified", 1, attributes={"project.name": slug})
        # Remember the orphaned pod so we don't re-spawn it blindly on the next pass.
        workers[wkey] = {
            "ticket_id": ticket.id,
            "project_dir": proj_str,
            "provider": provider.provider_name,
            "state": "error",
            "branch": branch,
            "trace_id": trace_id,
            "lifecycle_span_id": lifecycle_span_id,
            "spawned_at": utc_now_iso(),
            "error": err,
        }
        save_state(state)
        raise DispatchError(err, abort_project=True)

    # 4. Verified running -> claim the ticket (status only; the opt-in tag is user-owned).
    update_ticket_frontmatter(ticket.path, status="in_progress")
    refreshed = parse_ticket_file(ticket.path, project_dir=project_dir)

    # 5. Post-spawn housekeeping (best effort, never fatal):
    #    a) dismiss interactive harness start-up prompts (e.g. Claude's folder-trust dialog);
    #    b) if the runtime gave the worker an isolated workspace, make sure the ticket file is
    #       there too (``.tickets/`` may be untracked and therefore absent from a worktree).
    unblock_note = provider.post_spawn(proj_str, ticket.id, timeout_seconds=prompt_timeout)
    if unblock_note:
        telemetry.log_daemon("INFO", f"{ticket.id}: {unblock_note}", trace_id=trace_id, ticket_id=ticket.id)
    workspace = provider.workspace_path(proj_str, ticket.id)
    if workspace is not None:
        ws_ticket = workspace / ".tickets" / ticket.path.name
        if not ws_ticket.exists():
            ws_ticket.parent.mkdir(parents=True, exist_ok=True)
            ws_ticket.write_text(ticket.path.read_text(encoding="utf-8"), encoding="utf-8")
        telemetry.log_daemon(
            "INFO",
            f"{ticket.id}: isolated workspace {workspace}; ticket edits will be merged back",
            trace_id=trace_id,
            ticket_id=ticket.id,
        )

    telemetry.emit_span(
        name="taskforce.ticket.lifecycle",
        trace_id=trace_id,
        span_id=lifecycle_span_id,
        attributes={
            **base_attrs,
            "ticket.title": ticket.title,
            "ticket.status": "in_progress",
            "ticket.priority": ticket.priority,
            "ticket.tags": refreshed.tags,
        },
        events=[
            {
                "name": "ticket.claimed",
                "timestamp": utc_now_iso(),
                "attributes": {"opt_in_tag": claim_tag, "status": "in_progress"},
            }
        ],
    )
    spawn_span_id = telemetry.emit_span(
        name="taskforce.worker.spawn",
        trace_id=trace_id,
        parent_span_id=lifecycle_span_id,
        status_code="OK",
        attributes={**base_attrs, "worker.state": "running", "worker.verified": True},
    )
    telemetry.log_daemon(
        "INFO",
        f"Spawned & verified worker {ticket.id} in {proj_str} (branch={branch})",
        trace_id=trace_id,
        span_id=spawn_span_id,
        ticket_id=ticket.id,
        project=proj_str,
    )
    telemetry.log_worker(
        project_dir,
        ticket.id,
        f"Worker {ticket.id} spawned by provider '{provider.provider_name}' on branch '{branch}' and verified running",
        trace_id=trace_id,
    )
    telemetry.emit_metric(
        "taskforce.workers.spawned",
        1,
        attributes={"project.name": slug, "worker.provider": provider.provider_name},
    )
    workers[wkey] = {
        "ticket_id": ticket.id,
        "project_dir": proj_str,
        "provider": provider.provider_name,
        "state": "running",
        "branch": branch,
        "trace_id": trace_id,
        "lifecycle_span_id": lifecycle_span_id,
        "spawned_at": utc_now_iso(),
        "verified_at": utc_now_iso(),
        "paused_at": None,
        "last_note_hash": refreshed.last_note_hash,
        "feedback_cycles": 0,
    }
    save_state(state)
    return True


def pause_worker_for_ticket(
    project_dir: Path,
    ticket: TicketInfo,
    config: dict[str, Any],
    telemetry: TelemetryManager,
    provider: WorkerProvider,
    state: dict[str, Any],
    reason: str = "waiting-for-review",
) -> bool:
    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    w_entry = workers.get(wkey, {})
    trace_id = str(w_entry.get("trace_id") or new_trace_id())
    parent_span_id = w_entry.get("lifecycle_span_id")

    ok = provider.pause(proj_str, ticket.id)
    span_id = telemetry.emit_span(
        name="taskforce.worker.pause",
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        status_code="OK" if ok else "ERROR",
        attributes={
            "ticket.id": ticket.id,
            "project.path": proj_str,
            "project.name": project_slug(project_dir),
            "worker.id": ticket.id,
            "worker.provider": provider.provider_name,
            "worker.state": "paused",
            "pause.reason": reason,
        },
        events=[
            {
                "name": "worker.paused_for_review",
                "timestamp": utc_now_iso(),
                "attributes": {"reason": reason},
            }
        ],
    )
    telemetry.log_daemon(
        "INFO" if ok else "ERROR",
        f"Paused worker {ticket.id} in {proj_str} ({reason})"
        + ("" if ok else f" FAILED: {provider.last_error}"),
        trace_id=trace_id,
        span_id=span_id,
        ticket_id=ticket.id,
    )
    telemetry.log_worker(
        project_dir,
        ticket.id,
        f"Worker {ticket.id} paused ({reason})",
        trace_id=trace_id,
    )
    telemetry.emit_metric(
        "taskforce.workers.paused_for_review",
        1,
        attributes={"project.name": project_slug(project_dir)},
    )

    w_entry.update(
        {
            "ticket_id": ticket.id,
            "project_dir": proj_str,
            "provider": provider.provider_name,
            "state": "paused",
            "trace_id": trace_id,
            "paused_at": utc_now_iso(),
            "last_note_hash": ticket.last_note_hash,
        }
    )
    workers[wkey] = w_entry
    save_state(state)
    return ok


def mark_worker_lost(
    project_dir: Path,
    ticket: TicketInfo,
    telemetry: TelemetryManager,
    provider: WorkerProvider,
    state: dict[str, Any],
    observed_state: str,
) -> None:
    """Flag a tracked worker whose pod died/stopped without reporting back.

    The ticket is intentionally left ``in_progress`` (a human must triage: the pod may have
    partial work on its branch), but a note explains what happened and how to recover, and
    the worker no longer counts as running so the project is not blocked forever.
    """
    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    w_entry = workers.get(wkey, {})
    trace_id = str(w_entry.get("trace_id") or new_trace_id())
    reason = f"worker pod is {observed_state} and never reported back"

    span_id = telemetry.emit_span(
        name="taskforce.worker.lost",
        trace_id=trace_id,
        parent_span_id=w_entry.get("lifecycle_span_id"),
        status_code="ERROR",
        attributes={
            "ticket.id": ticket.id,
            "project.path": proj_str,
            "project.name": project_slug(project_dir),
            "worker.id": ticket.id,
            "worker.provider": provider.provider_name,
            "worker.state": "error",
            "worker.observed_state": observed_state,
        },
        events=[{"name": "worker.lost", "timestamp": utc_now_iso(), "attributes": {"reason": reason}}],
    )
    telemetry.log_daemon(
        "ERROR",
        f"Worker {ticket.id} in {proj_str} lost: {reason}",
        trace_id=trace_id,
        span_id=span_id,
        ticket_id=ticket.id,
    )
    telemetry.log_worker(project_dir, ticket.id, f"Worker {ticket.id} lost ({reason})", trace_id=trace_id)
    telemetry.emit_metric("taskforce.workers.lost", 1, attributes={"project.name": project_slug(project_dir)})

    append_ticket_note(
        ticket.path,
        "## Task Force: worker lost\n"
        f"The SCION worker pod for `{ticket.id}` is `{observed_state}` and did not report back "
        "(no `waiting-for-review` tag). The ticket is left `in_progress` for triage.\n"
        f"- Inspect: `tk scion-taskforce logs {ticket.id}` / `scion --project {proj_str} logs {ticket.id}`\n"
        f"- Retry: `tk reopen {ticket.id}` (keep the `taskforce` tag) — the daemon replaces the dead pod "
        "and relaunches on the next pass.\n"
        f"- Abandon: `tk reopen {ticket.id}` and remove the `taskforce` tag.",
    )

    w_entry.update(
        {
            "ticket_id": ticket.id,
            "project_dir": proj_str,
            "provider": provider.provider_name,
            "state": "error",
            "error": reason,
            "trace_id": trace_id,
            "ended_at": utc_now_iso(),
        }
    )
    workers[wkey] = w_entry
    save_state(state)


def send_feedback_to_worker(
    project_dir: Path,
    ticket_id: str,
    feedback_message: str | None,
    config: dict[str, Any],
    telemetry: TelemetryManager,
    provider: WorkerProvider,
    state: dict[str, Any],
    append_note_to_ticket: bool = True,
) -> bool:
    t_path = resolve_ticket_path(project_dir, ticket_id)
    if not t_path:
        raise ValueError(f"Ticket {ticket_id!r} not found in {project_dir}")

    ticket = parse_ticket_file(t_path, project_dir=project_dir)
    review_tag = str(config.get("tags", {}).get("review", "waiting-for-review"))
    claim_tag = str(config.get("tags", {}).get("claim", "taskforce"))

    note_ts = utc_now_iso()
    if append_note_to_ticket and feedback_message:
        note_ts = append_ticket_note(t_path, f"**Review Feedback:** {feedback_message}")
        ticket = parse_ticket_file(t_path, project_dir=project_dir)
    elif ticket.notes:
        note_ts, last_note_body = ticket.notes[-1]
        if not feedback_message:
            feedback_message = last_note_body

    # Remove waiting-for-review; keep the user's opt-in tag and status: in_progress
    remove_ticket_tag(t_path, review_tag)
    add_ticket_tag(t_path, claim_tag)
    update_ticket_frontmatter(t_path, status="in_progress")
    ticket = parse_ticket_file(t_path, project_dir=project_dir)

    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    w_entry = workers.get(wkey, {})
    trace_id = str(w_entry.get("trace_id") or new_trace_id())
    parent_span_id = w_entry.get("lifecycle_span_id")

    prompt_msg = (
        f"New review feedback was added to ticket `{ticket.id}` at {note_ts}:\n\n"
        f"{feedback_message or 'Please inspect the latest note in `tk show ' + ticket.id + '`.'}\n\n"
        f"Address the feedback, run tests, append an updated report via `tk add-note {ticket.id}`, "
        f"and re-add the `{review_tag}` tag when ready for review."
    )

    ok = provider.wake_with_message(proj_str, ticket.id, prompt_msg)
    cycles = int(w_entry.get("feedback_cycles", 0)) + 1

    span_id = telemetry.emit_span(
        name="taskforce.worker.feedback_wake",
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        status_code="OK" if ok else "ERROR",
        attributes={
            "ticket.id": ticket.id,
            "project.path": proj_str,
            "project.name": project_slug(project_dir),
            "worker.id": ticket.id,
            "worker.provider": provider.provider_name,
            "worker.state": "running",
            "feedback.note_timestamp": note_ts,
            "feedback.cycle": cycles,
        },
        events=[
            {
                "name": "worker.resumed_with_feedback",
                "timestamp": utc_now_iso(),
                "attributes": {"feedback.note_timestamp": note_ts},
            }
        ],
    )
    telemetry.log_daemon(
        "INFO" if ok else "ERROR",
        f"Woke worker {ticket.id} in {proj_str} with review feedback (cycle={cycles})"
        + ("" if ok else f" FAILED: {provider.last_error}"),
        trace_id=trace_id,
        span_id=span_id,
        ticket_id=ticket.id,
    )
    telemetry.log_worker(
        project_dir,
        ticket.id,
        f"Worker {ticket.id} resumed with feedback (cycle #{cycles}): {feedback_message}",
        trace_id=trace_id,
    )
    telemetry.emit_metric(
        "taskforce.workers.feedback_cycles",
        1,
        attributes={"project.name": project_slug(project_dir), "ticket.id": ticket.id},
    )

    w_entry.update(
        {
            "ticket_id": ticket.id,
            "project_dir": proj_str,
            "provider": provider.provider_name,
            "state": "running" if ok else w_entry.get("state", "paused"),
            "trace_id": trace_id,
            "paused_at": None if ok else w_entry.get("paused_at"),
            "last_note_hash": ticket.last_note_hash,
            "feedback_cycles": cycles,
        }
    )
    workers[wkey] = w_entry
    save_state(state)
    return ok


def run_gc(
    projects: list[str],
    config: dict[str, Any],
    telemetry: TelemetryManager,
    provider: WorkerProvider,
    state: dict[str, Any],
    force: bool = False,
) -> tuple[int, int]:
    """Run 5-day closed ticket pod GC and 30-day rotated log retention cleanup."""
    gc_days = int(config.get("watcher", {}).get("gc_retention_days", 5))
    cutoff_seconds = gc_days * 86400
    now_ts = time.time()

    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    deleted_pods = 0

    for proj_str in projects:
        proj_path = Path(proj_str)
        tickets_map = load_all_tickets(proj_path)

        for w_entry in list(workers.values()):
            if w_entry.get("project_dir") != proj_str:
                continue
            if w_entry.get("state") == "deleted":
                continue

            tid = str(w_entry.get("ticket_id", ""))
            t_info = tickets_map.get(tid)
            if t_info is None or t_info.status != "closed":
                continue

            if w_entry.get("state") == "running":
                pause_worker_for_ticket(
                    proj_path, t_info, config, telemetry, provider, state, reason="ticket-closed"
                )

            closed_ts = _parse_iso_ts(t_info.closed)
            if closed_ts is None:
                try:
                    closed_ts = t_info.path.stat().st_mtime
                except OSError:
                    closed_ts = now_ts

            age_seconds = max(0.0, now_ts - closed_ts)
            age_days = round(age_seconds / 86400.0, 2)

            if force or age_seconds >= cutoff_seconds:
                trace_id = str(w_entry.get("trace_id") or new_trace_id())
                parent_span_id = w_entry.get("lifecycle_span_id")
                ok = provider.delete(proj_str, tid, preserve_branch=True)
                telemetry.emit_span(
                    name="taskforce.worker.gc_delete",
                    trace_id=trace_id,
                    parent_span_id=parent_span_id,
                    status_code="OK" if ok else "ERROR",
                    attributes={
                        "ticket.id": tid,
                        "project.path": proj_str,
                        "project.name": project_slug(proj_path),
                        "worker.id": tid,
                        "worker.provider": provider.provider_name,
                        "worker.state": "deleted",
                        "gc.retention_days": gc_days,
                        "gc.ticket_closed_age_days": age_days,
                    },
                    events=[
                        {
                            "name": "worker.gc_deleted",
                            "timestamp": utc_now_iso(),
                            "attributes": {"age_days": age_days, "force": force},
                        }
                    ],
                )
                telemetry.log_daemon(
                    "INFO",
                    f"GC deleted worker pod {tid} in {proj_str} (closed_age_days={age_days})",
                    trace_id=trace_id,
                    ticket_id=tid,
                )
                telemetry.log_worker(
                    proj_path,
                    tid,
                    f"Worker pod {tid} deleted by 5-day GC (closed_age_days={age_days})",
                    trace_id=trace_id,
                )
                telemetry.emit_metric(
                    "taskforce.workers.gc_deleted",
                    1,
                    attributes={"project.name": project_slug(proj_path)},
                )
                w_entry["state"] = "deleted"
                w_entry["deleted_at"] = utc_now_iso()
                deleted_pods += 1

    save_state(state)
    purged_logs = telemetry.purge_expired_logs()
    return deleted_pods, purged_logs


def _count_running(workers: dict[str, dict[str, Any]], proj_str: str | None = None) -> int:
    return sum(
        1
        for w in workers.values()
        if w.get("state") == "running" and (proj_str is None or w.get("project_dir") == proj_str)
    )


def reconcile_once(
    projects: list[str],
    explicit_config: str | None = None,
    dry_run: bool = False,
    max_concurrent_override: int | None = None,
) -> dict[str, int]:
    """Execute one full multi-project reconciliation pass."""
    state = load_state()
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    stats = {
        "spawned": 0, "paused": 0, "woken": 0, "lost": 0, "gc_deleted": 0, "logs_purged": 0, "errors": 0,
    }

    global_cfg = load_config(explicit_config=explicit_config)
    watcher_cfg = global_cfg.get("watcher", {})
    max_total = (
        max_concurrent_override
        if max_concurrent_override is not None
        else int(watcher_cfg.get("max_concurrent", 10))
    )

    for raw_proj in projects:
        proj_path = Path(normalize_project_dir(raw_proj))
        proj_str = str(proj_path)
        if not (proj_path / ".tickets").exists():
            continue

        proj_cfg = load_config(project_dir=proj_path, explicit_config=explicit_config)
        proj_watcher = proj_cfg.get("watcher", {})
        max_per_proj = int(proj_watcher.get("max_concurrent_per_project", 10))
        auto_pause = bool(proj_watcher.get("auto_pause_on_review", True))
        auto_wake = bool(proj_watcher.get("auto_wake_on_feedback", True))
        review_tag = str(proj_cfg.get("tags", {}).get("review", "waiting-for-review"))

        telemetry = TelemetryManager(proj_cfg)
        provider = get_provider(proj_cfg, dry_run=dry_run)
        all_tickets = load_all_tickets(proj_path)

        # 0. Workers with an isolated workspace edit *their* copy of the ticket; merge the
        #    additive signals (notes, review tag) back into the project's .tickets/ first.
        merged_any = False
        for w_entry in list(workers.values()):
            if w_entry.get("project_dir") != proj_str or w_entry.get("state") not in ("running", "paused"):
                continue
            tid = str(w_entry.get("ticket_id", ""))
            t_info = all_tickets.get(tid)
            if t_info is None:
                continue
            workspace = provider.workspace_path(proj_str, tid)
            if workspace is None:
                continue
            merged = merge_worker_ticket_copy(t_info.path, workspace / ".tickets" / t_info.path.name, review_tag)
            if merged["notes"] or merged["review_tag"]:
                merged_any = True
                telemetry.log_daemon(
                    "INFO",
                    f"{tid}: merged {merged['notes']} note(s)"
                    + (f" and the '{review_tag}' tag" if merged["review_tag"] else "")
                    + " from the worker workspace",
                    ticket_id=tid,
                )
        if merged_any:
            all_tickets = load_all_tickets(proj_path)

        # 1. Existing tracked workers: review-pause or feedback-wake
        for w_entry in list(workers.values()):
            if w_entry.get("project_dir") != proj_str:
                continue
            tid = str(w_entry.get("ticket_id", ""))
            t_info = all_tickets.get(tid)
            if t_info is None:
                continue

            w_state = w_entry.get("state")
            if auto_pause and w_state == "running" and review_tag in t_info.tags:
                pause_worker_for_ticket(
                    proj_path, t_info, proj_cfg, telemetry, provider, state, reason=review_tag
                )
                stats["paused"] += 1
            elif (
                auto_wake
                and w_state == "paused"
                and t_info.status == "in_progress"
                and review_tag in t_info.tags
                and t_info.last_note_hash
                and t_info.last_note_hash != w_entry.get("last_note_hash", "")
            ):
                send_feedback_to_worker(
                    proj_path,
                    tid,
                    feedback_message=None,
                    config=proj_cfg,
                    telemetry=telemetry,
                    provider=provider,
                    state=state,
                    append_note_to_ticket=False,
                )
                stats["woken"] += 1

        # 1b. Liveness: a tracked "running" worker whose pod is gone/stopped/crashed and that
        #     never reported back (no review tag) is a ghost. Flag it so it stops occupying a
        #     concurrency slot and the human sees why the ticket is still in_progress.
        for w_entry in list(workers.values()):
            if w_entry.get("project_dir") != proj_str or w_entry.get("state") != "running":
                continue
            tid = str(w_entry.get("ticket_id", ""))
            t_info = all_tickets.get(tid)
            if t_info is None or review_tag in t_info.tags:
                continue
            live = provider.health(proj_str, tid)
            if live is not None and live.is_running:
                continue
            mark_worker_lost(proj_path, t_info, telemetry, provider, state, live.state if live else "missing")
            stats["lost"] += 1
            stats["errors"] += 1

        # 2. Dispatch opted-in ready tickets up to the concurrency limits.
        #    One preflight per project per pass; the first hard failure aborts this project.
        candidates = [
            t for t in get_ready_tickets(proj_path) if is_eligible_for_dispatch(t, proj_cfg)[0]
        ]
        if candidates:
            pre = provider.preflight(proj_str)
            _record_project_health(state, telemetry, proj_str, pre.ok, pre.message)
            if not pre.ok:
                stats["errors"] += 1
                candidates = []

        for candidate in candidates:
            if _count_running(workers) >= max_total or _count_running(workers, proj_str) >= max_per_proj:
                break
            existing_w = workers.get(_worker_key(proj_path, candidate.id))
            if existing_w and existing_w.get("state") in ("running", "paused"):
                continue
            try:
                if dispatch_ticket(
                    proj_path, candidate, proj_cfg, telemetry, provider, state, skip_preflight=True
                ):
                    stats["spawned"] += 1
            except DispatchError as exc:
                stats["errors"] += 1
                if exc.abort_project:
                    telemetry.log_daemon(
                        "WARNING",
                        f"Skipping remaining dispatches in {proj_str} this pass: {exc}",
                        project=proj_str,
                    )
                    break

        # 3. 5-day closed pod GC & 30-day log purge
        deleted, purged = run_gc([proj_str], proj_cfg, telemetry, provider, state, force=False)
        stats["gc_deleted"] += deleted
        stats["logs_purged"] += purged

    return stats


def run_daemon(
    initial_projects: list[str] | None = None,
    explicit_config: str | None = None,
    poll_interval_override: int | None = None,
    max_concurrent_override: int | None = None,
    dry_run: bool = False,
) -> int:
    """Continuous background daemon reconciliation loop across all registered projects."""
    running = True

    def _handle_sig(_signum: int, _frame: Any) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT, _handle_sig)

    state = load_state()
    if initial_projects:
        for p in initial_projects:
            norm = normalize_project_dir(p)
            if norm not in state["projects"]:
                state["projects"].append(norm)
        save_state(state)

    cfg = load_config(explicit_config=explicit_config)
    interval = (
        poll_interval_override
        if poll_interval_override is not None
        else int(cfg.get("watcher", {}).get("poll_interval_seconds", 15))
    )
    telemetry = TelemetryManager(cfg)
    telemetry.log_daemon(
        "INFO",
        f"tk-scion-taskforce daemon loop started (poll_interval={interval}s)",
        projects=state.get("projects", []),
    )

    while running:
        try:
            current_state = load_state()
            projects = list(current_state.get("projects", []))
            if projects:
                reconcile_once(
                    projects=projects,
                    explicit_config=explicit_config,
                    dry_run=dry_run,
                    max_concurrent_override=max_concurrent_override,
                )
        except Exception as exc:  # noqa: BLE001 - a bad pass must never kill the singleton daemon
            telemetry.log_daemon(
                "ERROR",
                f"Reconcile pass crashed: {exc!r}",
                traceback=traceback.format_exc(),
            )
            print(f"[tk-scion-taskforce] reconcile pass crashed: {exc!r}", flush=True)
            traceback.print_exc()
        for _ in range(max(1, interval * 2)):
            if not running:
                break
            time.sleep(0.5)

    telemetry.log_daemon("INFO", "tk-scion-taskforce daemon loop stopped cleanly")
    return 0
