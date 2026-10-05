"""Event-driven task force: react to one ticket save (``on-save``) or catch up once (``sync``).

The core ``tk`` post-write hook runs ``on-save <id>`` in the
background after every successful write (CLI or Web UI). Each run takes the per-project lock,
catches up on worker reports, then decides what to do for the saved ticket:

- tagged ``taskforce`` + open + deps closed + no worker -> note, start a Scion worker
- worker active + a human note was added              -> forward the note (wakes a paused worker)
- worker reported back (``waiting-for-review``)       -> pause it, freeing its slot
- no free slot                                        -> note "queued"
- ticket closed                                       -> stop its worker, start the next queued
- ticket reopened                                     -> drop ``waiting-for-review``, start a worker
- ``taskforce`` removed / ``no-taskforce`` added      -> stop and delete its worker (branch kept), note it
- ticket file deleted                                 -> stop and delete its worker (branch kept)
- otherwise                                           -> nothing

Status notes are written straight to the ticket file (not via ``tk``), so they never re-trigger
the hook. ``sync`` (and ``watch``, which repeats it) runs the same catch-up for saves the hook cannot
see (hand edits, ``git pull``, worker edits), flags workers whose pods died, and pauses workers whose
Scion activity says their turn ended without a report.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tk_scion_taskforce.config import load_config
from tk_scion_taskforce.providers.scion import ScionProvider
from tk_scion_taskforce.roles import select_roles
from tk_scion_taskforce.state import load_state, normalize_project_dir, save_state, state_lock
from tk_scion_taskforce.telemetry import TelemetryManager
from tk_scion_taskforce.tickets import (
    TicketInfo,
    get_ready_tickets,
    get_tickets_dir,
    load_all_tickets,
    merge_worker_ticket_copy,
    parse_ticket_file,
    remove_ticket_tag,
    validate_ticket_id,
)
from tk_scion_taskforce.workers import (
    PLUGIN_NOTE_PREFIXES,
    DispatchError,
    _count_running,
    _worker_key,
    dispatch_ticket,
    failure_hint,
    has_agent,
    is_eligible_for_dispatch,
    mark_worker_lost,
    max_workers_per_project,
    missing_skill_message,
    pause_worker_for_ticket,
    project_lock,
    send_feedback_to_worker,
    status_note,
    tags,
)

ACTIVE_STATES = ("running", "paused")
# Every state in which Scion may still hold an agent for the ticket (everything but "deleted").
LIVE_STATES = ("running", "paused", "stopped", "error")


@dataclass
class _Ctx:
    project: Path
    proj_str: str
    cfg: dict[str, Any]
    telemetry: TelemetryManager
    provider: ScionProvider
    state: dict[str, Any]
    paused: int = 0
    errors: int = 0
    error: str = ""  # detail of the last failed start, for `dispatch`
    skill_missing: bool = False  # the last start failed only because a role skill is not installed

    @property
    def workers(self) -> dict[str, dict[str, Any]]:
        return self.state.setdefault("workers", {})


def _context(project_dir: str | Path, explicit_config: str | None, dry_run: bool) -> _Ctx:
    project = Path(normalize_project_dir(project_dir))
    cfg = load_config(project_dir=project, explicit_config=explicit_config)
    return _Ctx(
        project=project,
        proj_str=str(project),
        cfg=cfg,
        telemetry=TelemetryManager(cfg),
        provider=ScionProvider(cfg, dry_run=dry_run),
        state={},  # loaded by each caller under project_lock + state_lock
    )


def _note(ticket_path: Path, text: str) -> None:
    status_note(ticket_path, text)


def _log_failure(ctx: _Ctx, tid: str, what: str, detail: str) -> None:
    """Full failure detail goes to the local logs only; ticket notes get ``failure_hint``."""
    ctx.telemetry.log_event("ERROR", f"{tid}: {what}: {detail}", ticket_id=tid)
    ctx.telemetry.log_worker(ctx.project, tid, f"{what}: {detail}")


def _project_workers(ctx: _Ctx, states: tuple[str, ...] = ACTIVE_STATES) -> list[dict[str, Any]]:
    return [w for w in ctx.workers.values() if w.get("project_dir") == ctx.proj_str and w.get("state") in states]


def _stop_worker(ctx: _Ctx, ticket: TicketInfo, entry: dict[str, Any]) -> None:
    if ctx.provider.stop(ctx.proj_str, ticket.id):
        entry["state"] = "stopped"
        _note(ticket.path, f"ticket closed; stopped worker `{ticket.id}`.")
        ctx.telemetry.log_event("INFO", f"{ticket.id}: ticket closed, worker stopped", ticket_id=ticket.id)
        return
    # The pod may still run in the shared checkout: keep the entry active so its slot stays taken
    # and the next save or `sync` retries the stop.
    _log_failure(ctx, ticket.id, "ticket closed, stopping the worker failed", ctx.provider.last_error)
    _note(ticket.path, f"ticket closed; could not stop worker `{ticket.id}`: {failure_hint(ctx.provider.last_error, ticket.id)}")


def _remove_worker(ctx: _Ctx, tid: str, entry: dict[str, Any], reason: str, ticket: TicketInfo | None) -> None:
    """Stop and delete the ticket's Scion agent, keeping its branch. Notes the ticket if it still exists."""
    if not has_agent(entry):
        # The start failed before Scion created an agent: nothing to stop, delete or note.
        entry["state"] = "deleted"
        ctx.telemetry.log_event("INFO", f"{tid}: {reason}; no Scion agent to remove", ticket_id=tid)
        return
    if entry.get("state") in ACTIVE_STATES:
        ctx.provider.stop(ctx.proj_str, tid)  # best effort; delete removes a stopped agent either way
    ok = ctx.provider.delete(ctx.proj_str, tid, preserve_branch=True)
    # Marked deleted even on failure so a missing agent is not retried (and re-noted) on every save.
    entry.update({"state": "deleted", "agent": False})
    branch = entry.get("branch")
    if ticket is not None:
        if ok:
            kept = f" (branch `{branch}` kept)" if branch else ""
            _note(ticket.path, f"{reason}; stopped and removed worker `{tid}`{kept}.")
        else:
            _note(ticket.path, f"{reason}; could not remove worker `{tid}`: {failure_hint(ctx.provider.last_error, tid)}")
    if ok:
        ctx.telemetry.log_event("INFO", f"{tid}: {reason}, worker removed", ticket_id=tid)
    else:
        _log_failure(ctx, tid, f"{reason}, removing the worker failed", ctx.provider.last_error)


def _merge_report(ctx: _Ctx, ticket: TicketInfo, review_tag: str) -> TicketInfo:
    """Merge the worker's workspace copy of the ticket (notes + review tag) into the project ticket."""
    workspace = ctx.provider.workspace_path(ctx.proj_str, ticket.id)
    if workspace is None:
        return ticket
    merged = merge_worker_ticket_copy(ticket.path, workspace / ".tickets" / ticket.path.name, review_tag)
    if not (merged["notes"] or merged["review_tag"]):
        return ticket
    ctx.telemetry.log_event(
        "INFO",
        f"{ticket.id}: merged {merged['notes']} note(s)"
        + (f" and the '{review_tag}' tag" if merged["review_tag"] else "")
        + " from the worker workspace",
        ticket_id=ticket.id,
    )
    return parse_ticket_file(ticket.path, project_dir=ctx.project)


def _refresh(ctx: _Ctx) -> None:
    """Keep each worker in step with its ticket: merge reports, pause reviewed workers, stop workers of
    closed tickets, remove workers whose ticket opted out or was deleted."""
    claim_tag, ignore_tag, review_tag = tags(ctx.cfg)
    tickets = load_all_tickets(ctx.project)
    for entry in _project_workers(ctx, LIVE_STATES):
        tid = str(entry.get("ticket_id", ""))
        ticket = tickets.get(tid)
        if ticket is None:
            _remove_worker(ctx, tid, entry, "ticket file deleted", None)
            continue
        active = entry.get("state") in ACTIVE_STATES
        if active:
            ticket = _merge_report(ctx, ticket, review_tag)
        if claim_tag not in ticket.tags or ignore_tag in ticket.tags:
            reason = f"`{claim_tag}` tag removed" if claim_tag not in ticket.tags else f"`{ignore_tag}` tag added"
            _remove_worker(ctx, tid, entry, reason, ticket)
        elif not active:
            continue
        elif ticket.status == "closed":
            _stop_worker(ctx, ticket, entry)
        elif review_tag in ticket.tags and entry.get("state") == "running":
            if pause_worker_for_ticket(ctx.project, ticket, ctx.telemetry, ctx.provider, ctx.state, reason=review_tag):
                ctx.paused += 1
    save_state(ctx.state)


def _has_slot(ctx: _Ctx) -> tuple[bool, int, int]:
    limit = max_workers_per_project(ctx.cfg)
    busy = _count_running(ctx.workers, ctx.proj_str)
    global_limit = int(ctx.cfg.get("watcher", {}).get("max_concurrent", 10))
    return busy < limit and _count_running(ctx.workers) < global_limit, busy, limit


def _start(ctx: _Ctx, ticket: TicketInfo, ack: str) -> bool:
    missing = select_roles(ctx.project, ticket.tags).missing
    if missing:
        # Not a runtime failure: only this ticket waits, so the queue keeps going (`skill_missing`).
        ctx.errors += 1
        ctx.skill_missing = True
        ctx.error = missing_skill_message(missing)
        ctx.telemetry.log_event("WARNING", f"{ticket.id}: {ctx.error}", ticket_id=ticket.id)
        entry = ctx.workers.setdefault(_worker_key(ctx.proj_str, ticket.id), {})
        entry.update({"ticket_id": ticket.id, "project_dir": ctx.proj_str, "state": "error", "error": ctx.error})
        _note(ticket.path, ctx.error)
        return False
    _note(ticket.path, ack)
    try:
        ok = dispatch_ticket(ctx.project, ticket, ctx.cfg, ctx.telemetry, ctx.provider, ctx.state)
    except DispatchError as exc:
        ctx.errors += 1
        ctx.error = str(exc)
        ctx.telemetry.log_event("ERROR", f"{ticket.id}: could not start a Scion worker: {exc}", ticket_id=ticket.id)
        # Record the failure so the queue does not retry it on every save of another ticket;
        # a save of this ticket or `sync` retries it. Keeps the entry's `agent` flag.
        entry = ctx.workers.setdefault(_worker_key(ctx.proj_str, ticket.id), {})
        entry.update({"ticket_id": ticket.id, "project_dir": ctx.proj_str, "state": "error", "error": str(exc)})
        _note(
            ticket.path,
            f"could not start a Scion worker: {failure_hint(str(exc), ticket.id)}\n"
            "Retry by saving the ticket again or with `tk scion-taskforce sync`.",
        )
        return False
    if ok:
        branch = ctx.workers.get(_worker_key(ctx.proj_str, ticket.id), {}).get("branch")
        _note(ticket.path, f"started Scion worker `{ticket.id}`" + (f" on branch `{branch}`." if branch else "."))
    else:
        ctx.error = f"a worker named `{ticket.id}` already exists in Scion; not starting another"
        _note(ticket.path, f"{ctx.error}.")
    return ok


def _start_queued(ctx: _Ctx, retry_errors: bool = False) -> int:
    """Start opted-in ready tickets while slots are free. Stops at the first launch failure.

    Tickets whose last start failed (state ``error``) are skipped unless ``retry_errors`` (``sync``),
    so a broken runtime does not retry and re-note them on every save of an unrelated ticket.
    """
    skip = ACTIVE_STATES if retry_errors else (*ACTIVE_STATES, "error")
    started = 0
    for ticket in get_ready_tickets(ctx.project):
        if not is_eligible_for_dispatch(ticket, ctx.cfg)[0]:
            continue
        if ctx.workers.get(_worker_key(ctx.proj_str, ticket.id), {}).get("state") in skip:
            continue
        if not _has_slot(ctx)[0]:
            break
        if not _start(ctx, ticket, "a worker slot is free; starting a new Scion worker."):
            if ctx.skill_missing:
                ctx.skill_missing = False
                continue
            break
        started += 1
    return started


def _saved_ticket_path(project: Path, ticket_id: str) -> Path | None:
    """Exact ``.tickets/<id>.md`` only. The hook passes the file's basename as the ID, and a
    substring match (as interactive commands allow) could resolve ``abc-1`` to ``abc-12``."""
    path = get_tickets_dir(project) / f"{validate_ticket_id(ticket_id)}.md"
    return path if path.is_file() else None


def on_save(
    project_dir: str | Path,
    ticket_id: str,
    event: str = "",
    explicit_config: str | None = None,
    dry_run: bool = False,
) -> str:
    """Handle one ticket save. Returns a one-line summary (written to the hook log)."""
    ctx = _context(project_dir, explicit_config, dry_run)
    with project_lock(ctx.project), state_lock():
        ctx.state = load_state()
        _refresh(ctx)
        t_path = _saved_ticket_path(ctx.project, ticket_id)
        if t_path is None:
            return f"{ticket_id}: not found"
        ticket = parse_ticket_file(t_path, project_dir=ctx.project)
        summary = _decide(ctx, ticket, event)
        started = _start_queued(ctx)
        save_state(ctx.state)
    return summary + (f"; started {started} queued" if started else "")


def _waiting_on(ctx: _Ctx, ticket: TicketInfo) -> list[str]:
    """Dependencies of ``ticket`` that are not closed yet (empty when it is ready)."""
    if ticket.id in {t.id for t in get_ready_tickets(ctx.project)}:
        return []
    tickets = load_all_tickets(ctx.project)
    return [d for d in ticket.deps if d not in tickets or tickets[d].status != "closed"]


def _decide(ctx: _Ctx, ticket: TicketInfo, event: str) -> str:
    claim_tag = tags(ctx.cfg)[0]
    entry = ctx.workers.get(_worker_key(ctx.proj_str, ticket.id))
    active = bool(entry) and entry.get("state") in ACTIVE_STATES

    if ticket.status == "closed":
        return f"{ticket.id}: closed"
    if claim_tag not in ticket.tags:
        return f"{ticket.id}: not tagged {claim_tag!r}; ignored"

    if active:
        last = ticket.notes[-1][1] if ticket.notes else ""
        if event == "add-note" and last and not last.startswith(PLUGIN_NOTE_PREFIXES):
            ok = send_feedback_to_worker(
                ctx.project, ticket.id, None, ctx.cfg, ctx.telemetry, ctx.provider, ctx.state,
                append_note_to_ticket=False,
            )
            if ok:
                _note(ticket.path, f"worker `{ticket.id}` is already in progress; forwarded the latest update.")
            else:
                hint = failure_hint(ctx.provider.last_error, ticket.id)
                _note(ticket.path, f"could not forward the update to worker `{ticket.id}`: {hint}")
            return f"{ticket.id}: forwarded note (ok={ok})"
        return f"{ticket.id}: worker already active"

    review_tag = tags(ctx.cfg)[2]
    if event in ("reopen", "status") and ticket.status == "open" and review_tag in ticket.tags:
        # Reopening means "do more work": the old review tag would block dispatch.
        remove_ticket_tag(ticket.path, review_tag)
        _note(ticket.path, f"ticket reopened; removed the `{review_tag}` tag.")
        ticket = parse_ticket_file(ticket.path, project_dir=ctx.project)

    eligible, reason = is_eligible_for_dispatch(ticket, ctx.cfg)
    if not eligible:
        return f"{ticket.id}: {reason}"
    waiting = _waiting_on(ctx, ticket)
    if waiting:
        _note(ticket.path, f"request noted; waiting on dependencies: {', '.join(waiting)}.")
        return f"{ticket.id}: waiting on deps"
    has_slot, busy, limit = _has_slot(ctx)
    if not has_slot:
        _note(ticket.path, f"request noted; queued ({busy} of {limit} workers busy). It starts when a slot frees.")
        return f"{ticket.id}: queued"
    ok = _start(ctx, ticket, "request noted; no existing worker found, starting a new Scion worker.")
    return f"{ticket.id}: started={ok}"


def dispatch_now(
    project_dir: str | Path,
    ticket_path: Path,
    explicit_config: str | None = None,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """`dispatch <id>`: the on-save checks (opt-in tag, status, dependencies) without the worker limit.
    Returns ``(started, reason)``."""
    ctx = _context(project_dir, explicit_config, dry_run)
    with project_lock(ctx.project), state_lock():
        ctx.state = load_state()
        ticket = parse_ticket_file(ticket_path, project_dir=ctx.project)
        entry = ctx.workers.get(_worker_key(ctx.proj_str, ticket.id), {})
        if entry.get("state") in ACTIVE_STATES:
            return False, f"its worker is already {entry['state']}"
        eligible, reason = is_eligible_for_dispatch(ticket, ctx.cfg)
        if not eligible:
            return False, reason
        waiting = _waiting_on(ctx, ticket)
        if waiting:
            return False, f"waiting on dependencies: {', '.join(waiting)}"
        ok = _start(ctx, ticket, "dispatched by hand; starting a new Scion worker (worker limit ignored).")
        save_state(ctx.state)
    return ok, ctx.error


def collect_reports(project_dir: str | Path, explicit_config: str | None = None) -> None:
    """Merge worker reports back into tickets (and pause reviewed workers) without starting anything."""
    ctx = _context(project_dir, explicit_config, dry_run=False)
    with project_lock(ctx.project), state_lock():
        ctx.state = load_state()
        _refresh(ctx)


def _check_pods(ctx: _Ctx, stats: dict[str, int]) -> None:
    """After refresh, check each still-running worker's pod.

    - Pod missing or not running: mark the worker lost (note on the ticket, slot freed).
    - Pod up but its Scion activity says the turn ended (``TURN_DONE_ACTIVITIES``), past
      ``watcher.turn_grace_seconds`` (a stale ``completed`` can linger right after a wake): merge the
      workspace report again, since it may have landed after refresh, then pause the worker. Without a
      report the ticket gets a note asking for direction.
    """
    review_tag = tags(ctx.cfg)[2]
    grace = float(ctx.cfg.get("watcher", {}).get("turn_grace_seconds", 60))
    tickets = load_all_tickets(ctx.project)
    for entry in _project_workers(ctx, ("running",)):
        ticket = tickets.get(str(entry.get("ticket_id", "")))
        if ticket is None:
            continue
        live = ctx.provider.health(ctx.proj_str, ticket.id)
        if live is None or not live.is_running:
            mark_worker_lost(ctx.project, ticket, ctx.telemetry, ctx.state, live.state if live else "missing")
            stats["lost"] += 1
            continue
        if not live.turn_done or time.time() - float(entry.get("turn_started") or 0) < grace:
            continue
        ticket = _merge_report(ctx, ticket, review_tag)
        reported = review_tag in ticket.tags
        reason = review_tag if reported else f"turn {live.activity}"
        if not pause_worker_for_ticket(ctx.project, ticket, ctx.telemetry, ctx.provider, ctx.state, reason=reason):
            continue
        ctx.paused += 1
        if not reported:
            _note(
                ticket.path,
                f"worker `{ticket.id}` stopped without a report (Scion activity: {live.activity}); paused it. "
                f"Add a note to answer or redirect it, or run `tk scion-taskforce attach {ticket.id}` to see "
                "its session.",
            )


def sync_project(
    project_dir: str | Path,
    explicit_config: str | None = None,
    dry_run: bool = False,
    check_liveness: bool = True,
    retry_errors: bool = True,
) -> dict[str, int]:
    """One-shot catch-up for saves the hook could not see. ``watch`` passes ``retry_errors=False`` so a
    broken runtime is not retried (and noted) on every pass."""
    ctx = _context(project_dir, explicit_config, dry_run)
    stats = {"started": 0, "paused": 0, "lost": 0, "errors": 0}
    with project_lock(ctx.project), state_lock():
        ctx.state = load_state()
        _refresh(ctx)
        # shortcut: pods are checked only by `sync`/`watch`, not on every save (one `scion list` per
        # worker); subscribe to Scion Hub notifications when reports must be picked up instantly.
        if check_liveness:
            _check_pods(ctx, stats)
        stats["started"] = _start_queued(ctx, retry_errors=retry_errors)
        stats["paused"], stats["errors"] = ctx.paused, ctx.errors + stats["lost"]
        save_state(ctx.state)
    return stats


def project_agents(project_dir: str | Path) -> list[str]:
    """Ticket IDs of this project's workers that may still hold a Scion agent."""
    proj_str = normalize_project_dir(project_dir)
    workers = load_state().get("workers", {}).values()
    return sorted(
        str(w.get("ticket_id")) for w in workers
        if w.get("project_dir") == proj_str and w.get("state") in LIVE_STATES and has_agent(w)
    )


def remove_project_workers(project_dir: str | Path, explicit_config: str | None = None, dry_run: bool = False) -> int:
    """Stop and delete every Scion agent of this project (branches kept), for `uninit`."""
    ctx = _context(project_dir, explicit_config, dry_run)
    with project_lock(ctx.project), state_lock():
        ctx.state = load_state()
        tickets = load_all_tickets(ctx.project)
        entries = [e for e in _project_workers(ctx, LIVE_STATES) if has_agent(e)]
        for entry in entries:
            tid = str(entry.get("ticket_id", ""))
            _remove_worker(ctx, tid, entry, "task force removed from this project", tickets.get(tid))
        save_state(ctx.state)
    return len(entries)


# --------------------------------------------------------------------------- hook install

HOOK_NAME = "scion-taskforce"
HOOK_SCRIPT = """#!/bin/sh
# Installed by `tk scion-taskforce hook install`: hand each ticket save to the Scion task force.
# Remove this file (or run `tk scion-taskforce hook uninstall`) to stop event-driven dispatch.
exec "${TK_SCRIPT:-tk}" scion-taskforce on-save "$TK_TICKET_ID" --event "$TK_EVENT"
"""


def hook_path(project_dir: str | Path) -> Path:
    return Path(normalize_project_dir(project_dir)) / ".tickets" / ".hooks" / "post-write.d" / HOOK_NAME


def _ensure_ignored(ignore_file: Path, lines: tuple[str, ...]) -> None:
    """Append the missing ``lines`` to a ``.gitignore``, keeping whatever is already there."""
    existing = ignore_file.read_text(encoding="utf-8") if ignore_file.exists() else ""
    missing = [line for line in lines if line not in existing.splitlines()]
    if missing:
        prefix = "" if not existing or existing.endswith("\n") else "\n"
        ignore_file.write_text(existing + prefix + "\n".join(missing) + "\n", encoding="utf-8")


def install_hook(project_dir: str | Path) -> Path:
    target = hook_path(project_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(HOOK_SCRIPT, encoding="utf-8")
    target.chmod(0o755)
    hooks_dir = target.parent.parent
    # Machine-local files: the hook log, this hook, and the telemetry log symlink (telemetry.py).
    _ensure_ignored(hooks_dir / ".gitignore", ("hooks.log", f"post-write.d/{HOOK_NAME}"))
    _ensure_ignored(hooks_dir.parent / ".gitignore", (".scion-taskforce-logs",))
    return target


def uninstall_hook(project_dir: str | Path) -> bool:
    target = hook_path(project_dir)
    if target.exists():
        target.unlink()
        return True
    return False
