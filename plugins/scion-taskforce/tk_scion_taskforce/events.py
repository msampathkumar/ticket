"""Event-driven task force: react to one ticket save (``on-save``) or catch up once (``sync``).

The core ``tk`` post-write hook runs ``on-save <id>`` in the
background after every successful write (CLI or Web UI). Each run takes the per-project lock,
catches up on worker reports, then decides what to do for the saved ticket:

- tagged ``taskforce`` + open + deps closed + no worker -> note, start a Scion worker
- worker active + a human note was added              -> forward the note (wakes a paused worker)
- worker reported back (``waiting-for-review``)       -> pause it, freeing its slot
- no free slot                                        -> note "queued"
- ticket closed                                       -> stop its worker, start the next queued
- otherwise                                           -> nothing

Status notes are written straight to the ticket file (not via ``tk``), so they never re-trigger
the hook. ``sync`` runs the same catch-up for saves the hook cannot see (hand edits, ``git pull``,
worker edits) and also flags workers whose pods died.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tk_scion_taskforce.config import load_config
from tk_scion_taskforce.providers import WorkerProvider, get_provider
from tk_scion_taskforce.state import load_state, normalize_project_dir, save_state
from tk_scion_taskforce.telemetry import TelemetryManager, utc_now_iso
from tk_scion_taskforce.tickets import (
    TicketInfo,
    append_ticket_note,
    get_ready_tickets,
    load_all_tickets,
    merge_worker_ticket_copy,
    parse_ticket_file,
    resolve_ticket_path,
)
from tk_scion_taskforce.workers import (
    DispatchError,
    _count_running,
    _worker_key,
    dispatch_ticket,
    is_eligible_for_dispatch,
    mark_worker_lost,
    max_workers_per_project,
    pause_worker_for_ticket,
    project_lock,
    send_feedback_to_worker,
)

NOTE_PREFIX = "**Task Force:**"
ACTIVE_STATES = ("running", "paused")


@dataclass
class _Ctx:
    project: Path
    proj_str: str
    cfg: dict[str, Any]
    telemetry: TelemetryManager
    provider: WorkerProvider
    state: dict[str, Any]
    paused: int = 0
    errors: int = 0

    @property
    def workers(self) -> dict[str, dict[str, Any]]:
        return self.state.setdefault("workers", {})

    def tag(self, name: str, default: str) -> str:
        return str(self.cfg.get("tags", {}).get(name, default))


def _context(project_dir: str | Path, explicit_config: str | None, dry_run: bool) -> _Ctx:
    project = Path(normalize_project_dir(project_dir))
    cfg = load_config(project_dir=project, explicit_config=explicit_config)
    return _Ctx(
        project=project,
        proj_str=str(project),
        cfg=cfg,
        telemetry=TelemetryManager(cfg),
        provider=get_provider(cfg, dry_run=dry_run),
        state=load_state(),
    )


def _note(ticket_path: Path, text: str) -> None:
    """Append a status note unless it would repeat the ticket's latest note."""
    body = f"{NOTE_PREFIX} {text}"
    info = parse_ticket_file(ticket_path)
    if info.notes and info.notes[-1][1] == body:
        return
    append_ticket_note(ticket_path, body)


def _project_workers(ctx: _Ctx, states: tuple[str, ...] = ACTIVE_STATES) -> list[dict[str, Any]]:
    return [w for w in ctx.workers.values() if w.get("project_dir") == ctx.proj_str and w.get("state") in states]


def _stop_worker(ctx: _Ctx, ticket: TicketInfo, entry: dict[str, Any]) -> None:
    ok = ctx.provider.pause(ctx.proj_str, ticket.id)
    entry.update({"state": "stopped", "ended_at": utc_now_iso()})
    if ok:
        _note(ticket.path, f"ticket closed; stopped worker `{ticket.id}`.")
    else:
        _note(ticket.path, f"ticket closed; could not stop worker `{ticket.id}`: {ctx.provider.last_error}")
    ctx.telemetry.log_event("INFO" if ok else "ERROR", f"{ticket.id}: ticket closed, worker stop ok={ok}", ticket_id=ticket.id)


def _refresh(ctx: _Ctx) -> None:
    """Catch up on worker reports: merge isolated-workspace notes, pause reviewed workers, stop closed tickets."""
    # shortcut: worker reports are picked up on the next save or `sync`, not when written; subscribe to
    # Scion notifications (`scion notifications subscribe --triggers COMPLETED,WAITING_FOR_INPUT`) when
    # review latency matters.
    review_tag = ctx.tag("review", "waiting-for-review")
    tickets = load_all_tickets(ctx.project)
    for entry in _project_workers(ctx):
        tid = str(entry.get("ticket_id", ""))
        ticket = tickets.get(tid)
        if ticket is None:
            continue
        workspace = ctx.provider.workspace_path(ctx.proj_str, tid)
        if workspace is not None:
            merged = merge_worker_ticket_copy(ticket.path, workspace / ".tickets" / ticket.path.name, review_tag)
            if merged["notes"] or merged["review_tag"]:
                ctx.telemetry.log_event(
                    "INFO",
                    f"{tid}: merged {merged['notes']} note(s)"
                    + (f" and the '{review_tag}' tag" if merged["review_tag"] else "")
                    + " from the worker workspace",
                    ticket_id=tid,
                )
                ticket = parse_ticket_file(ticket.path, project_dir=ctx.project)
        if ticket.status == "closed":
            _stop_worker(ctx, ticket, entry)
        elif review_tag in ticket.tags and entry.get("state") == "running":
            pause_worker_for_ticket(ctx.project, ticket, ctx.cfg, ctx.telemetry, ctx.provider, ctx.state, reason=review_tag)
            ctx.paused += 1
    save_state(ctx.state)


def _has_slot(ctx: _Ctx) -> tuple[bool, int, int]:
    limit = max_workers_per_project(ctx.cfg, ctx.project)
    busy = _count_running(ctx.workers, ctx.proj_str)
    global_limit = int(ctx.cfg.get("watcher", {}).get("max_concurrent", 10))
    return busy < limit and _count_running(ctx.workers) < global_limit, busy, limit


def _start(ctx: _Ctx, ticket: TicketInfo, ack: str) -> bool:
    _note(ticket.path, ack)
    try:
        ok = dispatch_ticket(ctx.project, ticket, ctx.cfg, ctx.telemetry, ctx.provider, ctx.state)
    except DispatchError as exc:
        ctx.errors += 1
        _note(
            ticket.path,
            f"could not start a Scion worker: {str(exc)[:400]}\n"
            "Retry by saving the ticket again or with `tk scion-taskforce sync`.",
        )
        return False
    if ok:
        branch = ctx.workers.get(_worker_key(ctx.proj_str, ticket.id), {}).get("branch", ticket.id)
        _note(ticket.path, f"started Scion worker `{ticket.id}` on branch `{branch}`.")
    else:
        _note(ticket.path, f"a worker named `{ticket.id}` already exists in Scion; not starting another.")
    return ok


def _start_queued(ctx: _Ctx) -> int:
    """Start opted-in ready tickets while slots are free. Stops at the first launch failure."""
    started = 0
    for ticket in get_ready_tickets(ctx.project):
        if not is_eligible_for_dispatch(ticket, ctx.cfg)[0]:
            continue
        if ctx.workers.get(_worker_key(ctx.proj_str, ticket.id), {}).get("state") in ACTIVE_STATES:
            continue
        if not _has_slot(ctx)[0]:
            break
        if not _start(ctx, ticket, "a worker slot is free; starting a new Scion worker."):
            break
        started += 1
    return started


def on_save(
    project_dir: str | Path,
    ticket_id: str,
    event: str = "",
    explicit_config: str | None = None,
    dry_run: bool = False,
) -> str:
    """Handle one ticket save. Returns a one-line summary (written to the hook log)."""
    ctx = _context(project_dir, explicit_config, dry_run)
    with project_lock(ctx.project):
        ctx.state = load_state()  # re-read under the lock
        _refresh(ctx)
        t_path = resolve_ticket_path(ctx.project, ticket_id)
        if t_path is None:
            return f"{ticket_id}: not found"
        ticket = parse_ticket_file(t_path, project_dir=ctx.project)
        summary = _decide(ctx, ticket, event)
        started = _start_queued(ctx)
        save_state(ctx.state)
    return summary + (f"; started {started} queued" if started else "")


def _decide(ctx: _Ctx, ticket: TicketInfo, event: str) -> str:
    claim_tag = ctx.tag("claim", "taskforce")
    entry = ctx.workers.get(_worker_key(ctx.proj_str, ticket.id))
    active = bool(entry) and entry.get("state") in ACTIVE_STATES

    if ticket.status == "closed":
        return f"{ticket.id}: closed"
    if claim_tag not in ticket.tags:
        return f"{ticket.id}: not tagged {claim_tag!r}; ignored"

    if active:
        last = ticket.notes[-1][1] if ticket.notes else ""
        if event == "add-note" and last and not last.startswith(NOTE_PREFIX):
            ok = send_feedback_to_worker(
                ctx.project, ticket.id, None, ctx.cfg, ctx.telemetry, ctx.provider, ctx.state,
                append_note_to_ticket=False,
            )
            if ok:
                _note(ticket.path, f"worker `{ticket.id}` is already in progress; forwarded the latest update.")
            else:
                _note(ticket.path, f"could not forward the update to worker `{ticket.id}`: {ctx.provider.last_error}")
            return f"{ticket.id}: forwarded note (ok={ok})"
        return f"{ticket.id}: worker already active"

    eligible, reason = is_eligible_for_dispatch(ticket, ctx.cfg)
    if not eligible:
        return f"{ticket.id}: {reason}"
    if ticket.id not in {t.id for t in get_ready_tickets(ctx.project)}:
        tickets = load_all_tickets(ctx.project)
        waiting = [d for d in ticket.deps if d not in tickets or tickets[d].status != "closed"]
        _note(ticket.path, f"request noted; waiting on dependencies: {', '.join(waiting)}.")
        return f"{ticket.id}: waiting on deps"
    has_slot, busy, limit = _has_slot(ctx)
    if not has_slot:
        _note(ticket.path, f"request noted; queued ({busy} of {limit} workers busy). It starts when a slot frees.")
        return f"{ticket.id}: queued"
    ok = _start(ctx, ticket, "request noted; no existing worker found, starting a new Scion worker.")
    return f"{ticket.id}: started={ok}"


def sync_project(
    project_dir: str | Path,
    explicit_config: str | None = None,
    dry_run: bool = False,
    check_liveness: bool = True,
) -> dict[str, int]:
    """One-shot catch-up for saves the hook could not see."""
    ctx = _context(project_dir, explicit_config, dry_run)
    stats = {"started": 0, "paused": 0, "lost": 0, "errors": 0}
    with project_lock(ctx.project):
        ctx.state = load_state()
        _refresh(ctx)
        # shortcut: dead pods are detected only by `sync`; run it from cron or a Scion notification when
        # lost workers holding slots becomes a problem.
        if check_liveness:
            tickets = load_all_tickets(ctx.project)
            for entry in _project_workers(ctx, ("running",)):
                ticket = tickets.get(str(entry.get("ticket_id", "")))
                if ticket is None:
                    continue
                live = ctx.provider.health(ctx.proj_str, ticket.id)
                if live is None or not live.is_running:
                    mark_worker_lost(
                        ctx.project, ticket, ctx.telemetry, ctx.provider, ctx.state, live.state if live else "missing"
                    )
                    stats["lost"] += 1
        stats["started"] = _start_queued(ctx)
        stats["paused"], stats["errors"] = ctx.paused, ctx.errors + stats["lost"]
        save_state(ctx.state)
    return stats


# --------------------------------------------------------------------------- hook install

HOOK_NAME = "scion-taskforce"
HOOK_SCRIPT = """#!/bin/sh
# Installed by `tk scion-taskforce hook install`: hand each ticket save to the Scion task force.
# Remove this file (or run `tk scion-taskforce hook uninstall`) to stop event-driven dispatch.
exec "${TK_SCRIPT:-tk}" scion-taskforce on-save "$TK_TICKET_ID" --event "$TK_EVENT"
"""


def hook_path(project_dir: str | Path) -> Path:
    return Path(normalize_project_dir(project_dir)) / ".tickets" / ".hooks" / "post-write.d" / HOOK_NAME


def install_hook(project_dir: str | Path) -> Path:
    target = hook_path(project_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(HOOK_SCRIPT, encoding="utf-8")
    target.chmod(0o755)
    ignore = target.parent.parent / ".gitignore"
    if not ignore.exists():
        ignore.write_text("hooks.log\n", encoding="utf-8")
    return target


def uninstall_hook(project_dir: str | Path) -> bool:
    target = hook_path(project_dir)
    if target.exists():
        target.unlink()
        return True
    return False
