"""Command-line interface for tk-scion-taskforce."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from tk_scion_taskforce import __version__
from tk_scion_taskforce.config import init_config, load_config, resolve_config_path, uninit_config
from tk_scion_taskforce.daemon import (
    DispatchError,
    dispatch_ticket,
    is_eligible_for_dispatch,
    pause_worker_for_ticket,
    reconcile_once,
    run_daemon,
    run_gc,
    send_feedback_to_worker,
)
from tk_scion_taskforce.providers import get_provider
from tk_scion_taskforce.server import (
    add_project,
    list_projects,
    load_state,
    normalize_project_dir,
    remove_project,
    restart_server,
    start_server,
    status_server,
    stop_project,
    stop_server,
)
from tk_scion_taskforce.telemetry import TelemetryManager, new_trace_id, project_slug
from tk_scion_taskforce.tickets import parse_ticket_file, resolve_ticket_path

HELP_TEXT = """tk-scion-taskforce - Autonomous SCION task force orchestrator plugin for tk

Usage:
  tk scion-taskforce [--config <path>] <subcommand> [args...]

Daemon & Multi-Project Management (Single Global Instance):
  start [dir]                      Start the task force for project [dir] (default: cwd);
                                   boots the single global daemon if it is not running
  stop [dir] | stop --all          Stop the task force for ONE project (pause its workers, unregister;
                                   daemon exits when no projects remain) or stop everything (--all)
  status                           Show daemon status, watched projects, provider health, worker counts
  restart [dir]                    Restart the global daemon
  server start|status|stop|restart Explicit global daemon lifecycle commands
  project add <dir>                Register a project directory with the global task force
  project stop|remove <dir>        Stop the task force for a project (alias of 'stop <dir>')
  project list                     List all registered project directories

Opt-in model: the task force only picks up READY tickets that YOU tagged `taskforce`
(tags.claim). It never adds that tag itself. A pod must be verified running before a
ticket is moved to in_progress; failures leave the ticket untouched.

Task Force Operations:
  init [--global] [--force]        Initialize project-scoped .scion-taskforce/ directory & templates
  uninit [--global]                Remove project-scoped .scion-taskforce/ directory & unregister project
  watch [dir] [--interval <sec>] [--max-concurrent <n>] [--once] [--dry-run]
                                   Run the task force reconciler in the foreground
  dispatch [<id>] [--dry-run]      Claim and spawn worker(s) for <id> or all ready tickets
  list | ps                        List all tracked task force workers across projects
  feedback <id> "<msg>"            Add review feedback note, remove waiting-for-review, & wake worker
  attach <id>                      Attach interactively to worker <id>
  pause <id>                       Manually pause worker <id>
  logs [<id>]                      View local OpenTelemetry daemon or worker logs (including .gz)
  brief <id>                       View the persisted worker brief for worker <id>
  trace [<id>]                     Inspect OpenTelemetry trace spans (filtered by ticket <id>)
  gc [--force]                     Run 5-day closed pod GC and 30-day rotated log cleanup
  version                          Print plugin version
  help                             Show this help message
"""


def _infer_project_dir() -> Path:
    tickets_env = os.environ.get("TICKETS_DIR")
    if tickets_env:
        tp = Path(tickets_env).expanduser().resolve()
        if tp.name == ".tickets":
            return tp.parent
        return tp
    return Path.cwd().resolve()


def _find_ticket_across_projects(
    ticket_id: str,
    default_project: Path,
) -> tuple[Path, Path]:
    t_path = resolve_ticket_path(default_project, ticket_id)
    if t_path:
        return default_project, t_path
    for proj_str in list_projects():
        proj_p = Path(proj_str)
        t_path = resolve_ticket_path(proj_p, ticket_id)
        if t_path:
            return proj_p, t_path
    raise ValueError(f"Ticket {ticket_id!r} not found in {default_project} or registered projects.")


def _extract_global_flags(argv: list[str]) -> tuple[str | None, bool, list[str]]:
    explicit_config: str | None = None
    dry_run = False
    remaining: list[str] = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--config" and i + 1 < len(argv):
            explicit_config = argv[i + 1]
            i += 2
        elif arg.startswith("--config="):
            explicit_config = arg.split("=", 1)[1]
            i += 1
        elif arg == "--dry-run":
            dry_run = True
            i += 1
        else:
            remaining.append(arg)
            i += 1
    return explicit_config, dry_run, remaining


def cmd_init(args: list[str], project_dir: Path) -> int:
    global_scope = "--global" in args or "-g" in args
    force = "--force" in args or "-f" in args
    scope_desc = "global scope" if global_scope else f"project scope at `{project_dir}`"
    print(f"🚀 Initializing SCION Task Force ({scope_desc})...")
    target, archived_count = init_config(project_dir=project_dir, global_scope=global_scope, force=force)
    if archived_count > 0:
        print(f"📦 Archived {archived_count} existing configuration/prompt file(s) with timestamped .old suffixes.")
    print(f"📁 Created/Updated configuration directory & templates:")
    print(f"   • Path: `{target.parent}`")
    print(f"   • `scion-taskforce.yaml` — Task force orchestrator configuration (claim tags, concurrency limits, provider rules)")
    print(f"   • `prompt.md`           — Default customizable autonomous worker brief template")
    print(f"✅ Initialization successful! You can now run 'tk scion-taskforce start' to launch the task force.")
    return 0


def cmd_uninit(args: list[str], project_dir: Path) -> int:
    global_scope = "--global" in args or "-g" in args
    scope_desc = "global config" if global_scope else f"project directory `{project_dir}`"
    print(f"🗑️ Uninitializing SCION Task Force for {scope_desc}...")
    success, path = uninit_config(project_dir=project_dir, global_scope=global_scope)
    if success:
        if not global_scope:
            removed = remove_project(project_dir)
            if removed:
                print(f"ℹ️ Unregistered project `{project_dir}` from global daemon state registry.")
        print(f"✅ Successfully removed `{path}`.")
    else:
        print(f"ℹ️ No SCION task force configuration found at `{path}`.")
    return 0


def cmd_project(args: list[str], default_project: Path) -> int:
    action = args[0] if args else "list"
    if action == "add":
        target = args[1] if len(args) > 1 else str(default_project)
        norm = add_project(target)
        print(f"✅ Registered project with scion-taskforce: {norm}")
        return 0
    if action in ("remove", "rm", "stop"):
        target = args[1] if len(args) > 1 else str(default_project)
        return stop_project(target)
    if action in ("list", "ls"):
        projs = list_projects()
        if not projs:
            print("No projects registered with tk-scion-taskforce.")
            return 0
        print(f"Registered projects ({len(projs)}):")
        for p in projs:
            print(f"  - {p}")
        return 0
    print(f"Unknown project subcommand: {action}", file=sys.stderr)
    return 1


def cmd_dispatch(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    provider = get_provider(cfg, dry_run=dry_run)
    state = load_state()
    add_project(project_dir)
    state = load_state()

    ticket_arg = next((a for a in args if not a.startswith("-")), None)
    if ticket_arg:
        proj, t_path = _find_ticket_across_projects(ticket_arg, project_dir)
        ticket = parse_ticket_file(t_path, project_dir=proj)
        eligible, reason = is_eligible_for_dispatch(ticket, cfg)
        if not eligible:
            claim_tag = str(cfg.get("tags", {}).get("claim", "taskforce"))
            print(f"⏭️  Not dispatching {ticket.id}: {reason}.")
            print(f"   Opt a ticket in with: tk update {ticket.id} --tags <existing>,{claim_tag}")
            return 1
        try:
            ok = dispatch_ticket(proj, ticket, cfg, telemetry, provider, state)
        except DispatchError as exc:
            print(f"❌ Could not launch a verified worker for '{ticket.id}': {exc}", file=sys.stderr)
            print("   Ticket left untouched. Check the provider runtime (e.g. `podman machine start`).", file=sys.stderr)
            return 1
        if ok:
            print(f"🚀 Dispatched & verified task force worker '{ticket.id}' in {proj}")
            return 0
        print(f"❌ Did not dispatch worker for ticket '{ticket.id}' (see `tk scion-taskforce logs`)", file=sys.stderr)
        return 1

    stats = reconcile_once(
        projects=[str(project_dir)],
        explicit_config=explicit_config,
        dry_run=dry_run,
    )
    print(
        f"✅ Reconcile complete: spawned={stats['spawned']}, "
        f"paused={stats['paused']}, woken={stats['woken']}, lost={stats.get('lost', 0)}, "
        f"gc_deleted={stats['gc_deleted']}, errors={stats['errors']}"
    )
    return 0


def cmd_list(project_dir: Path, explicit_config: str | None) -> int:
    state = load_state()
    workers: dict[str, dict[str, Any]] = state.get("workers", {})
    if not workers:
        print("No task force workers tracked yet.")
        return 0

    print(f"{'WORKER ID':<14} {'STATE':<10} {'PROVIDER':<10} {'CYCLES':<7} {'PROJECT':<30} {'TRACE ID'}")
    print("-" * 105)
    # states: running | paused | error (spawned but never verified) | deleted
    for w in sorted(workers.values(), key=lambda x: (str(x.get("project_dir", "")), str(x.get("ticket_id", "")))):
        wid = str(w.get("ticket_id", ""))
        st = str(w.get("state", "unknown"))
        prov = str(w.get("provider", "scion"))
        cycles = int(w.get("feedback_cycles", 0))
        proj = str(w.get("project_dir", str(project_dir)))
        trace_id = str(w.get("trace_id", ""))
        print(f"{wid:<14} {st:<10} {prov:<10} {cycles:<7} {proj:<30} {trace_id}")
    return 0


def cmd_feedback(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    pos = [a for a in args if not a.startswith("-")]
    if len(pos) < 2:
        print('Usage: tk scion-taskforce feedback <ticket-id> "<feedback-message>"', file=sys.stderr)
        return 1
    ticket_id = pos[0]
    feedback_msg = " ".join(pos[1:])
    proj, _ = _find_ticket_across_projects(ticket_id, project_dir)
    cfg = load_config(project_dir=proj, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    provider = get_provider(cfg, dry_run=dry_run)
    state = load_state()

    ok = send_feedback_to_worker(
        project_dir=proj,
        ticket_id=ticket_id,
        feedback_message=feedback_msg,
        config=cfg,
        telemetry=telemetry,
        provider=provider,
        state=state,
        append_note_to_ticket=True,
    )
    if ok:
        print(f"💬 Feedback added to {ticket_id}, removed waiting-for-review, and woke worker.")
        return 0
    print(f"❌ Failed to wake worker {ticket_id}", file=sys.stderr)
    return 1


def cmd_pause(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    pos = [a for a in args if not a.startswith("-")]
    if not pos:
        print("Usage: tk scion-taskforce pause <ticket-id>", file=sys.stderr)
        return 1
    ticket_id = pos[0]
    proj, t_path = _find_ticket_across_projects(ticket_id, project_dir)
    ticket = parse_ticket_file(t_path, project_dir=proj)
    cfg = load_config(project_dir=proj, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    provider = get_provider(cfg, dry_run=dry_run)
    state = load_state()

    ok = pause_worker_for_ticket(
        project_dir=proj,
        ticket=ticket,
        config=cfg,
        telemetry=telemetry,
        provider=provider,
        state=state,
        reason="manual-pause",
    )
    if ok:
        print(f"⏸️  Paused worker {ticket.id} in {proj}")
        return 0
    print(f"❌ Failed to pause worker {ticket.id}", file=sys.stderr)
    return 1


def cmd_attach(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    pos = [a for a in args if not a.startswith("-")]
    if not pos:
        print("Usage: tk scion-taskforce attach <ticket-id>", file=sys.stderr)
        return 1
    ticket_id = pos[0]
    proj, t_path = _find_ticket_across_projects(ticket_id, project_dir)
    ticket = parse_ticket_file(t_path, project_dir=proj)
    cfg = load_config(project_dir=proj, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    provider = get_provider(cfg, dry_run=dry_run)
    state = load_state()
    wkey = f"{normalize_project_dir(proj)}::{ticket.id}"
    w_entry = state.get("workers", {}).get(wkey, {})
    trace_id = str(w_entry.get("trace_id") or new_trace_id())

    cmd = provider.attach_command(str(proj), ticket.id)
    telemetry.emit_span(
        name="taskforce.worker.attach",
        trace_id=trace_id,
        parent_span_id=w_entry.get("lifecycle_span_id"),
        attributes={
            "ticket.id": ticket.id,
            "project.path": str(proj),
            "project.name": project_slug(proj),
            "worker.id": ticket.id,
            "worker.provider": provider.provider_name,
        },
    )
    telemetry.log_worker(proj, ticket.id, f"Interactive attach requested: {' '.join(cmd)}", trace_id=trace_id)

    if dry_run or os.environ.get("TK_SCION_TASKFORCE_DRY_RUN", "").lower() in ("1", "true", "yes"):
        print(f"🔗 [dry-run] Attach command: {' '.join(cmd)}")
        return 0

    res = subprocess.run(cmd, cwd=str(proj), check=False)
    return res.returncode


def cmd_logs(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
) -> int:
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    pos = [a for a in args if not a.startswith("-")]

    if not pos:
        lines = telemetry.read_daemon_logs(limit=200)
        if not lines:
            print(f"No daemon logs found at {telemetry.daemon_log_file}")
            return 0
        for line in lines:
            print(line)
        return 0

    ticket_id = pos[0]
    try:
        proj, t_path = _find_ticket_across_projects(ticket_id, project_dir)
        canonical_id = parse_ticket_file(t_path, project_dir=proj).id
    except ValueError:
        proj = project_dir
        canonical_id = ticket_id

    lines = telemetry.read_worker_logs(proj, canonical_id, limit=200)
    if not lines:
        print(f"No local logs found for worker {canonical_id}.")
        return 0
    for line in lines:
        print(line)
    return 0


def cmd_brief(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
) -> int:
    pos = [a for a in args if not a.startswith("-")]
    if not pos:
        print("Usage: tk scion-taskforce brief <ticket-id>", file=sys.stderr)
        return 1
    ticket_id = pos[0]
    try:
        proj, t_path = _find_ticket_across_projects(ticket_id, project_dir)
        canonical_id = parse_ticket_file(t_path, project_dir=proj).id
    except ValueError:
        proj = project_dir
        canonical_id = ticket_id

    cfg = load_config(project_dir=proj, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    brief = telemetry.read_worker_brief(proj, canonical_id)
    if not brief:
        print(f"No persisted worker brief found for worker {canonical_id}.", file=sys.stderr)
        return 1
    print(brief)
    return 0


def cmd_trace(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
) -> int:
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    pos = [a for a in args if not a.startswith("-")]
    ticket_id: str | None = None
    if pos:
        try:
            proj, t_path = _find_ticket_across_projects(pos[0], project_dir)
            ticket_id = parse_ticket_file(t_path, project_dir=proj).id
        except ValueError:
            ticket_id = pos[0]

    spans = telemetry.read_spans(ticket_id=ticket_id)
    if not spans:
        target_label = f" for ticket {ticket_id}" if ticket_id else ""
        print(f"No OpenTelemetry spans found{target_label} in {telemetry.traces_file}")
        return 0

    print(f"{'TIMESTAMP':<22} {'SPAN NAME':<28} {'STATUS':<8} {'TICKET':<12} {'TRACE ID'}")
    print("-" * 106)
    for sp in spans:
        ts = str(sp.get("timestamp", ""))
        name = str(sp.get("name", ""))
        status = str(sp.get("status", {}).get("code", "OK"))
        attrs = sp.get("attributes", {})
        tid = str(attrs.get("ticket.id") or attrs.get("worker.id") or "-")
        tr_id = str(sp.get("trace_id", ""))
        print(f"{ts:<22} {name:<28} {status:<8} {tid:<12} {tr_id}")
    return 0


def cmd_gc(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    force = "--force" in args or "-f" in args
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    telemetry = TelemetryManager(cfg)
    provider = get_provider(cfg, dry_run=dry_run)
    state = load_state()
    projects = list(state.get("projects", []))
    norm_default = normalize_project_dir(project_dir)
    if norm_default not in projects:
        projects.append(norm_default)

    deleted_pods, purged_logs = run_gc(
        projects=projects,
        config=cfg,
        telemetry=telemetry,
        provider=provider,
        state=state,
        force=force,
    )
    print(
        f"🧹 GC complete: deleted_closed_pods={deleted_pods} "
        f"(retention={cfg['watcher']['gc_retention_days']}d), "
        f"purged_rotated_logs={purged_logs} "
        f"(retention={cfg['telemetry']['rotation']['retention_days']}d)"
    )
    return 0


def cmd_watch(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    once = "--once" in args
    interval: int | None = None
    max_concurrent: int | None = None
    dir_arg: str | None = None

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--interval" and i + 1 < len(args):
            interval = int(args[i + 1])
            i += 2
        elif a == "--max-concurrent" and i + 1 < len(args):
            max_concurrent = int(args[i + 1])
            i += 2
        elif a == "--once":
            i += 1
        elif not a.startswith("-") and dir_arg is None:
            dir_arg = a
            i += 1
        else:
            i += 1

    target_proj = normalize_project_dir(dir_arg or project_dir)
    add_project(target_proj)

    if once:
        projs = list_projects() or [target_proj]
        stats = reconcile_once(
            projects=projs,
            explicit_config=explicit_config,
            dry_run=dry_run,
            max_concurrent_override=max_concurrent,
        )
        print(
            f"✅ Reconcile pass complete: spawned={stats['spawned']}, "
            f"paused={stats['paused']}, woken={stats['woken']}, lost={stats.get('lost', 0)}, "
            f"gc_deleted={stats['gc_deleted']}, errors={stats['errors']}"
        )
        return 0

    return run_daemon(
        initial_projects=[target_proj],
        explicit_config=explicit_config,
        poll_interval_override=interval,
        max_concurrent_override=max_concurrent,
        dry_run=dry_run,
    )


def main(argv: list[str] | None = None) -> int:
    raw_args = list(sys.argv[1:] if argv is None else argv)
    explicit_config, dry_run, args = _extract_global_flags(raw_args)
    project_dir = _infer_project_dir()

    if not args or args[0] in ("help", "--help", "-h"):
        print(HELP_TEXT.strip())
        return 0

    subcmd = args[0]
    subargs = args[1:]

    if subcmd in ("version", "--version", "-v"):
        cfg_path = resolve_config_path(project_dir=project_dir, explicit_config=explicit_config)
        print(f"tk-scion-taskforce {__version__}")
        if cfg_path:
            print(f"Active config: {cfg_path}")
        return 0

    if subcmd == "init":
        return cmd_init(subargs, project_dir)

    if subcmd == "uninit":
        return cmd_uninit(subargs, project_dir)

    if subcmd == "project":
        return cmd_project(subargs, project_dir)

    if subcmd == "server":
        action = subargs[0] if subargs else "status"
        rest = subargs[1:] if len(subargs) > 1 else []
        target_dir = rest[0] if rest and not rest[0].startswith("-") else str(project_dir)
        cfg = load_config(project_dir=Path(target_dir), explicit_config=explicit_config)
        tel = TelemetryManager(cfg)
        if action == "start":
            return start_server(directory=target_dir, explicit_config=explicit_config)
        if action == "stop":
            return stop_server()
        if action == "restart":
            return restart_server(directory=target_dir, explicit_config=explicit_config)
        return status_server(log_dir=tel.log_dir)

    if subcmd == "start":
        target_dir = subargs[0] if subargs and not subargs[0].startswith("-") else str(project_dir)
        return start_server(directory=target_dir, explicit_config=explicit_config)

    if subcmd == "stop":
        if "--all" in subargs:
            return stop_server()
        target = next((a for a in subargs if not a.startswith("-")), None)
        if target:
            return stop_project(target, explicit_config=explicit_config)
        # No project given: if exactly this cwd is registered, stop it; otherwise stop the daemon.
        if normalize_project_dir(project_dir) in list_projects():
            return stop_project(project_dir, explicit_config=explicit_config)
        return stop_server()

    if subcmd == "restart":
        target_dir = subargs[0] if subargs and not subargs[0].startswith("-") else str(project_dir)
        return restart_server(directory=target_dir, explicit_config=explicit_config)

    if subcmd == "status":
        cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
        tel = TelemetryManager(cfg)
        return status_server(log_dir=tel.log_dir)

    if subcmd == "watch":
        return cmd_watch(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "dispatch":
        return cmd_dispatch(subargs, project_dir, explicit_config, dry_run)

    if subcmd in ("list", "ps"):
        return cmd_list(project_dir, explicit_config)

    if subcmd == "feedback":
        return cmd_feedback(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "pause":
        return cmd_pause(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "attach":
        return cmd_attach(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "logs":
        return cmd_logs(subargs, project_dir, explicit_config)

    if subcmd == "brief":
        return cmd_brief(subargs, project_dir, explicit_config)

    if subcmd == "trace":
        return cmd_trace(subargs, project_dir, explicit_config)

    if subcmd == "gc":
        return cmd_gc(subargs, project_dir, explicit_config, dry_run)

    print(f"Unknown subcommand: {subcmd!r}. Run 'tk scion-taskforce help' for usage.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
