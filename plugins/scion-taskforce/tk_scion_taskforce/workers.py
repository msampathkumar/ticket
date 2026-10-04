"""Worker lifecycle for tk-scion-taskforce: verified launch, pause, feedback relay, liveness, GC, locks."""

from __future__ import annotations

import fcntl
import hashlib
import time
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from tk_scion_taskforce.providers.scion import ScionProvider
from tk_scion_taskforce.state import get_state_dir, normalize_project_dir, save_state
from tk_scion_taskforce.telemetry import (
    TelemetryManager,
    new_span_id,
    new_trace_id,
    project_slug,
    utc_now_iso,
)
from tk_scion_taskforce.tickets import (
    TicketInfo,
    append_ticket_note,
    load_all_tickets,
    parse_ticket_file,
    remove_ticket_tag,
    resolve_ticket_path,
    run_tk_show,
    update_ticket_frontmatter,
)

NOTE_PREFIX = "**Task Force:**"
FEEDBACK_PREFIX = "**Review Feedback:**"
# Notes the plugin writes itself; a ticket whose latest note starts with one is not forwarded to the worker.
PLUGIN_NOTE_PREFIXES = (NOTE_PREFIX, FEEDBACK_PREFIX, "## Task Force:")


def status_note(ticket_path: Path, text: str) -> None:
    """Append a ``**Task Force:**`` status note unless it would repeat the ticket's latest note."""
    body = f"{NOTE_PREFIX} {text}"
    info = parse_ticket_file(ticket_path)
    if info.notes and info.notes[-1][1] == body:
        return
    append_ticket_note(ticket_path, body)


def failure_hint(detail: str, ticket_id: str) -> str:
    """First line of ``detail``, cut to 120 chars, for a ticket note (ticket files are committed to git).
    The full detail goes to the local logs only."""
    first = next((line.strip() for line in str(detail or "").splitlines() if line.strip()), "unknown error")
    short = first if len(first) <= 120 else first[:117] + "..."
    return f"{short} (see `tk scion-taskforce logs {ticket_id}`)"


class DispatchError(Exception):
    """Raised when Scion cannot launch a verified worker; the ticket is left untouched."""


def _worker_key(project_dir: str | Path, ticket_id: str) -> str:
    return f"{normalize_project_dir(project_dir)}::{ticket_id}"


def tags(config: dict[str, Any]) -> tuple[str, str, str]:
    """The ``(claim, ignore, review)`` tag names from ``config``."""
    cfg = config.get("tags") or {}
    return (
        str(cfg.get("claim", "taskforce")),
        str(cfg.get("ignore", "no-taskforce")),
        str(cfg.get("review", "waiting-for-review")),
    )


def has_agent(entry: dict[str, Any]) -> bool:
    """Whether Scion may hold an agent for this worker entry. ``False`` when the start failed before
    Scion accepted a spawn (nothing to stop or delete). Entries from older versions lack the flag."""
    return bool(entry.get("agent", entry.get("state") != "error"))


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
    claim_tag, _, review_tag = tags(config)
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
    claim_tag, ignore_tag, review_tag = tags(config)
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
        telemetry.log_event(
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


def _record(
    telemetry: TelemetryManager,
    project_dir: Path,
    ticket_id: str,
    span: str,
    ok: bool,
    message: str,
    *,
    trace_id: str,
    parent_span_id: str | None = None,
    attrs: dict[str, Any] | None = None,
    event: tuple[str, dict[str, Any]] | None = None,
    worker_line: str | None = None,
    metric: str | None = None,
    metric_attrs: dict[str, Any] | None = None,
) -> str:
    """Write one worker lifecycle step to every sink: a span, ``taskforce.log``, the worker log and,
    when ``metric`` is set, a counter. Returns the span ID."""
    slug = project_slug(project_dir)
    span_id = telemetry.emit_span(
        name=span,
        trace_id=trace_id,
        parent_span_id=parent_span_id,
        status_code="OK" if ok else "ERROR",
        attributes={
            "ticket.id": ticket_id,
            "project.path": normalize_project_dir(project_dir),
            "project.name": slug,
            "worker.id": ticket_id,
            **(attrs or {}),
        },
        events=[{"name": event[0], "timestamp": utc_now_iso(), "attributes": event[1]}] if event else None,
    )
    telemetry.log_event("INFO" if ok else "ERROR", message, trace_id=trace_id, span_id=span_id, ticket_id=ticket_id)
    telemetry.log_worker(project_dir, ticket_id, worker_line or message, trace_id=trace_id)
    if metric:
        telemetry.emit_metric(metric, 1, attributes={"project.name": slug, **(metric_attrs or {})})
    return span_id


def dispatch_ticket(
    project_dir: Path,
    ticket: TicketInfo,
    config: dict[str, Any],
    telemetry: TelemetryManager,
    provider: ScionProvider,
    state: dict[str, Any],
) -> bool:
    """Launch a worker for ``ticket`` and claim it ONLY after the pod is verified running.

    Raises ``DispatchError`` when Scion cannot launch a verified worker. Returns ``False`` when a
    pod with this ID already exists and is left alone.
    """
    watcher_cfg = config.get("watcher", {})
    verify_timeout = float(watcher_cfg.get("spawn_verify_timeout_seconds", 30))
    verify_poll = float(watcher_cfg.get("spawn_verify_poll_seconds", 2))

    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})

    trace_id = new_trace_id()
    lifecycle_span_id = new_span_id()
    branch = provider.format_branch(ticket.id)
    slug = project_slug(project_dir)

    # 0. Pre-flight: is the provider runtime (podman/docker/k8s) reachable at all?
    pre = provider.preflight(proj_str)
    _record_project_health(state, telemetry, proj_str, pre.ok, pre.message)
    if not pre.ok:
        telemetry.log_worker(project_dir, ticket.id, f"Provider preflight failed: {pre.message}", trace_id=trace_id)
        raise DispatchError(f"provider preflight failed: {pre.message}")

    # 1. Idempotency: adopt an already-running pod with this ID instead of double-spawning.
    existing = provider.health(proj_str, ticket.id)
    if existing is not None and existing.is_running:
        telemetry.log_event(
            "WARNING",
            f"Adopting pre-existing running worker {ticket.id} in {proj_str}",
            trace_id=trace_id,
            ticket_id=ticket.id,
        )
    elif existing is not None:
        # A dead pod left behind by a previous attempt (worker state 'error'/'deleted', or the
        # ticket was explicitly reopened by a human) is replaced; anything else is left alone.
        prev = workers.get(wkey, {})
        retry_ok = prev.get("state") in ("error", "deleted", "stopped") or not prev
        if retry_ok and provider.delete(proj_str, ticket.id, preserve_branch=True):
            telemetry.log_event(
                "WARNING",
                f"Replaced stale {existing.state!r} pod for {ticket.id} in {proj_str} before relaunch",
                trace_id=trace_id,
                ticket_id=ticket.id,
            )
            existing = None  # the slot is free now; fall through to a fresh spawn
        else:
            telemetry.log_event(
                "WARNING",
                f"Worker {ticket.id} already exists in state {existing.state!r}; "
                f"not spawning (use 'tk scion-taskforce attach {ticket.id}' or delete the pod)",
                trace_id=trace_id,
                ticket_id=ticket.id,
            )
            return False

    telemetry.ensure_project_symlink(project_dir)
    prompt = build_worker_prompt(ticket, config, branch=branch)
    telemetry.save_worker_brief(project_dir, ticket.id, prompt)
    worker_env = {
        "OTEL_EXPORTER_OTLP_TRACES_FILE": str(telemetry.traces_file),
        "OTEL_EXPORTER_OTLP_METRICS_FILE": str(telemetry.metrics_file),
        "OTEL_RESOURCE_ATTRIBUTES": (
            f"service.name=scion-worker,ticket.id={ticket.id},"
            f"worker.id={ticket.id},project.name={slug}"
        ),
        "TRACEPARENT": f"00-{trace_id}-{lifecycle_span_id}-01",
    }

    def record_spawn(ok: bool, message: str, worker_line: str, metric: str, attrs: dict[str, Any]) -> None:
        _record(
            telemetry, project_dir, ticket.id, "taskforce.worker.spawn", ok, message,
            trace_id=trace_id, parent_span_id=lifecycle_span_id,
            attrs={"worker.branch": branch, **attrs}, worker_line=worker_line, metric=metric,
        )

    # 2. Spawn (request accepted by provider?)
    if existing is None and not provider.spawn(
        project_dir=proj_str, worker_id=ticket.id, prompt=prompt, branch=branch, env=worker_env
    ):
        err = provider.last_error or "provider.spawn returned False"
        record_spawn(
            False, f"Spawn FAILED for {ticket.id} in {proj_str}; ticket left untouched: {err}",
            f"Spawn failed: {err}", "taskforce.workers.spawn_failed",
            {"worker.state": "error", "error.message": err},
        )
        _record_project_health(state, telemetry, proj_str, False, err)
        raise DispatchError(err)

    # 3. Verify the pod actually exists and is running (NOT fire-and-forget).
    status = provider.wait_until_running(
        proj_str, ticket.id, timeout_seconds=verify_timeout, poll_seconds=verify_poll
    )
    entry = {
        "ticket_id": ticket.id,
        "project_dir": proj_str,
        "agent": True,  # Scion accepted the spawn (or the pod already existed)
        "branch": branch,
        "trace_id": trace_id,
        "lifecycle_span_id": lifecycle_span_id,
    }
    if status is None or not status.is_running:
        observed = status.state if status else "not_found"
        err = (
            f"worker {ticket.id} did not reach 'running' within {verify_timeout:.0f}s "
            f"(observed: {observed}). {provider.last_error}".strip()
        )
        record_spawn(
            False, f"Spawn verification FAILED for {ticket.id} in {proj_str}; ticket left untouched: {err}",
            f"Spawn verification failed: {err}", "taskforce.workers.spawn_unverified",
            {"worker.state": observed, "error.message": err},
        )
        # Remember the orphaned pod so we don't re-spawn it blindly on the next pass.
        workers[wkey] = {**entry, "state": "error", "error": err}
        save_state(state)
        raise DispatchError(err)

    # 4. Verified running -> claim the ticket (status only; the opt-in tag is user-owned).
    update_ticket_frontmatter(ticket.path, status="in_progress")
    refreshed = parse_ticket_file(ticket.path, project_dir=project_dir)

    # 5. If the runtime gave the worker an isolated workspace, make sure the ticket file is there
    #    too (``.tickets/`` may be untracked and therefore absent from a worktree).
    workspace = provider.workspace_path(proj_str, ticket.id)
    if workspace is not None:
        ws_ticket = workspace / ".tickets" / ticket.path.name
        if not ws_ticket.exists():
            ws_ticket.parent.mkdir(parents=True, exist_ok=True)
            ws_ticket.write_text(ticket.path.read_text(encoding="utf-8"), encoding="utf-8")
        telemetry.log_event(
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
            "ticket.id": ticket.id,
            "project.path": proj_str,
            "project.name": slug,
            "worker.id": ticket.id,
            "worker.branch": branch,
            "ticket.title": ticket.title,
            "ticket.status": "in_progress",
            "ticket.priority": ticket.priority,
            "ticket.tags": refreshed.tags,
        },
        events=[
            {
                "name": "ticket.claimed",
                "timestamp": utc_now_iso(),
                "attributes": {"opt_in_tag": tags(config)[0], "status": "in_progress"},
            }
        ],
    )
    record_spawn(
        True, f"Spawned & verified worker {ticket.id} in {proj_str} (branch={branch})",
        f"Worker {ticket.id} spawned on branch '{branch}' and verified running", "taskforce.workers.spawned",
        {"worker.state": "running", "worker.verified": True},
    )
    workers[wkey] = {**entry, "state": "running", "feedback_cycles": 0}
    save_state(state)
    return True


def pause_worker_for_ticket(
    project_dir: Path,
    ticket: TicketInfo,
    telemetry: TelemetryManager,
    provider: ScionProvider,
    state: dict[str, Any],
    reason: str = "waiting-for-review",
) -> bool:
    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    w_entry = workers.get(wkey, {})
    trace_id = str(w_entry.get("trace_id") or new_trace_id())

    ok = provider.pause(proj_str, ticket.id)
    _record(
        telemetry, project_dir, ticket.id, "taskforce.worker.pause", ok,
        f"Paused worker {ticket.id} in {proj_str} ({reason})" + ("" if ok else f" FAILED: {provider.last_error}"),
        trace_id=trace_id,
        parent_span_id=w_entry.get("lifecycle_span_id"),
        attrs={"worker.state": "paused", "pause.reason": reason},
        event=("worker.paused_for_review", {"reason": reason}),
        worker_line=f"Worker {ticket.id} paused ({reason})" if ok else f"Pausing worker {ticket.id} FAILED: {provider.last_error}",
        metric="taskforce.workers.paused_for_review" if ok else None,
    )
    if not ok:
        # The pod may still be running in the shared checkout: keep it `running` so its slot stays taken.
        status_note(ticket.path, f"could not pause worker `{ticket.id}`: {failure_hint(provider.last_error, ticket.id)}")
        return False

    w_entry.update({"ticket_id": ticket.id, "project_dir": proj_str, "state": "paused", "trace_id": trace_id})
    workers[wkey] = w_entry
    save_state(state)
    return True


def mark_worker_lost(
    project_dir: Path,
    ticket: TicketInfo,
    telemetry: TelemetryManager,
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

    _record(
        telemetry, project_dir, ticket.id, "taskforce.worker.lost", False,
        f"Worker {ticket.id} in {proj_str} lost: {reason}",
        trace_id=trace_id,
        parent_span_id=w_entry.get("lifecycle_span_id"),
        attrs={"worker.state": "error", "worker.observed_state": observed_state},
        event=("worker.lost", {"reason": reason}),
        worker_line=f"Worker {ticket.id} lost ({reason})",
        metric="taskforce.workers.lost",
    )

    append_ticket_note(
        ticket.path,
        "## Task Force: worker lost\n"
        f"The SCION worker pod for `{ticket.id}` is `{observed_state}` and did not report back "
        "(no `waiting-for-review` tag). The ticket is left `in_progress` for triage.\n"
        f"- Inspect: `tk scion-taskforce logs {ticket.id}` / `scion --project {proj_str} logs {ticket.id}`\n"
        f"- Retry: `tk reopen {ticket.id}` (keep the `taskforce` tag) — the save hook replaces the dead pod "
        "and relaunches it.\n"
        f"- Abandon: `tk reopen {ticket.id}` and remove the `taskforce` tag.",
    )

    w_entry.update(
        {"ticket_id": ticket.id, "project_dir": proj_str, "state": "error", "agent": True, "error": reason, "trace_id": trace_id}
    )
    workers[wkey] = w_entry
    save_state(state)


def send_feedback_to_worker(
    project_dir: Path,
    ticket_id: str,
    feedback_message: str | None,
    config: dict[str, Any],
    telemetry: TelemetryManager,
    provider: ScionProvider,
    state: dict[str, Any],
    append_note_to_ticket: bool = True,
) -> bool:
    t_path = resolve_ticket_path(project_dir, ticket_id)
    if not t_path:
        raise ValueError(f"Ticket {ticket_id!r} not found in {project_dir}")

    ticket = parse_ticket_file(t_path, project_dir=project_dir)
    review_tag = tags(config)[2]

    note_ts = utc_now_iso()
    if not (append_note_to_ticket and feedback_message) and ticket.notes:
        note_ts, last_note_body = ticket.notes[-1]
        if not feedback_message:
            feedback_message = last_note_body

    proj_str = normalize_project_dir(project_dir)
    wkey = _worker_key(proj_str, ticket.id)
    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    w_entry = workers.get(wkey, {})
    trace_id = str(w_entry.get("trace_id") or new_trace_id())

    prompt_msg = (
        f"New review feedback was added to ticket `{ticket.id}` at {note_ts}:\n\n"
        f"{feedback_message or 'Please inspect the latest note in `tk show ' + ticket.id + '`.'}\n\n"
        f"Address the feedback, run tests, append an updated report via `tk add-note {ticket.id}`, "
        f"and re-add the `{review_tag}` tag when ready for review."
    )

    # Wake first: the ticket changes only once the worker has actually received the feedback.
    ok = provider.wake_with_message(proj_str, ticket.id, prompt_msg)
    if ok:
        if append_note_to_ticket and feedback_message:
            note_ts = append_ticket_note(t_path, f"{FEEDBACK_PREFIX} {feedback_message}")
        # Clear the review tag (the opt-in tag is user-owned and left alone) in the project ticket and
        # in an isolated workspace copy, so the next merge does not re-add it and re-pause the worker.
        remove_ticket_tag(t_path, review_tag)
        if ticket.status != "closed":
            update_ticket_frontmatter(t_path, status="in_progress")
        workspace = provider.workspace_path(project_dir, ticket.id)
        if workspace:
            worker_ticket = workspace / ".tickets" / t_path.name
            if worker_ticket.is_file():
                remove_ticket_tag(worker_ticket, review_tag)
    cycles = int(w_entry.get("feedback_cycles", 0)) + (1 if ok else 0)

    _record(
        telemetry, project_dir, ticket.id, "taskforce.worker.feedback_wake", ok,
        f"Woke worker {ticket.id} in {proj_str} with review feedback (cycle={cycles})"
        + ("" if ok else f" FAILED: {provider.last_error}"),
        trace_id=trace_id,
        parent_span_id=w_entry.get("lifecycle_span_id"),
        attrs={"worker.state": "running", "feedback.note_timestamp": note_ts, "feedback.cycle": cycles},
        event=("worker.resumed_with_feedback", {"feedback.note_timestamp": note_ts}),
        worker_line=(
            f"Worker {ticket.id} resumed with feedback (cycle #{cycles}): {feedback_message}"
            if ok
            else f"Waking worker {ticket.id} with feedback FAILED: {provider.last_error}"
        ),
        metric="taskforce.workers.feedback_cycles" if ok else None,
        metric_attrs={"ticket.id": ticket.id},
    )

    w_entry.update(
        {
            "ticket_id": ticket.id,
            "project_dir": proj_str,
            "state": "running" if ok else w_entry.get("state", "paused"),
            "trace_id": trace_id,
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
    provider: ScionProvider,
    state: dict[str, Any],
    force: bool = False,
) -> tuple[int, int]:
    """Delete the Scion agents of tickets closed for ``gc_retention_days``; purge rotated logs.

    Workers of closed tickets were already stopped by the save hook (or `sync`). A failed delete
    keeps the entry, so the next `gc` retries it.
    """
    gc_days = int(config.get("watcher", {}).get("gc_retention_days", 5))
    cutoff_seconds = gc_days * 86400
    now_ts = time.time()

    workers: dict[str, dict[str, Any]] = state.setdefault("workers", {})
    deleted_pods = 0

    for proj_str in projects:
        proj_path = Path(proj_str)
        tickets_map = load_all_tickets(proj_path)

        for w_entry in list(workers.values()):
            if w_entry.get("project_dir") != proj_str or w_entry.get("state") == "deleted":
                continue
            tid = str(w_entry.get("ticket_id", ""))
            t_info = tickets_map.get(tid)
            if t_info is None or t_info.status != "closed":
                continue

            closed_ts = _parse_iso_ts(t_info.closed)
            if closed_ts is None:
                try:
                    closed_ts = t_info.path.stat().st_mtime
                except OSError:
                    closed_ts = now_ts
            age_seconds = max(0.0, now_ts - closed_ts)
            age_days = round(age_seconds / 86400.0, 2)
            if not (force or age_seconds >= cutoff_seconds):
                continue
            if not has_agent(w_entry):
                w_entry["state"] = "deleted"  # the start failed before Scion created anything
                continue

            ok = provider.delete(proj_str, tid, preserve_branch=True)
            _record(
                telemetry, proj_path, tid, "taskforce.worker.gc_delete", ok,
                f"GC deleted worker pod {tid} in {proj_str} (closed_age_days={age_days})"
                if ok
                else f"GC could not delete worker pod {tid} in {proj_str}; kept for the next gc: {provider.last_error}",
                trace_id=str(w_entry.get("trace_id") or new_trace_id()),
                parent_span_id=w_entry.get("lifecycle_span_id"),
                attrs={
                    "worker.state": "deleted" if ok else str(w_entry.get("state")),
                    "gc.retention_days": gc_days,
                    "gc.ticket_closed_age_days": age_days,
                },
                event=("worker.gc_deleted", {"age_days": age_days, "force": force}) if ok else None,
                metric="taskforce.workers.gc_deleted" if ok else None,
            )
            if ok:
                w_entry.update({"state": "deleted", "agent": False})
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


def max_workers_per_project(proj_cfg: dict[str, Any]) -> int:
    """Per-project worker limit. Workers mount the shared checkout, so the default is 1."""
    return int(proj_cfg.get("watcher", {}).get("max_concurrent_per_project", 1))


@contextmanager
def project_lock(proj_path: Path) -> Iterator[None]:
    """Hold the per-project lock so background hooks and manual commands never overwrite each other's state."""
    lock_dir = get_state_dir() / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha1(str(proj_path).encode()).hexdigest()[:12]
    with open(lock_dir / f"{project_slug(proj_path)}-{digest}.lock", "w", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield  # closing the file releases the flock
