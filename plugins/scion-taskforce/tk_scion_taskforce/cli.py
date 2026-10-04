"""Command-line interface for tk-scion-taskforce."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tk_scion_taskforce import __version__
from tk_scion_taskforce.config import (
    init_config,
    load_config,
    resolve_config_path,
    uninit_config,
)
from tk_scion_taskforce.events import hook_path, install_hook, on_save, sync_project, uninstall_hook
from tk_scion_taskforce.providers import get_provider
from tk_scion_taskforce.state import known_projects, load_state, normalize_project_dir
from tk_scion_taskforce.telemetry import TelemetryManager, new_trace_id, project_slug
from tk_scion_taskforce.tickets import parse_ticket_file, resolve_ticket_path
from tk_scion_taskforce.workers import (
    DispatchError,
    dispatch_ticket,
    is_eligible_for_dispatch,
    pause_worker_for_ticket,
    project_lock,
    run_gc,
    send_feedback_to_worker,
)

HELP_TEXT = """tk-scion-taskforce - Autonomous SCION task force orchestrator plugin for tk

Usage:
  tk scion-taskforce [--config <path>] [--dry-run] <subcommand> [args...]

`init` installs a tk post-write hook. Every ticket save (CLI or Web UI) runs `on-save <id>`
in the background: a READY ticket YOU tagged `taskforce` gets a status note and a Scion worker;
a note added to a ticket with an active worker is forwarded to it; a worker that reports back
(`waiting-for-review`) is paused; closing a ticket stops its worker and starts the next queued one.

Setup:
  init [--global] [--force] [--defaults]
                                   Setup wizard: config, SCION template, Hub link, save hook
  uninit [--global]                Remove .scion-taskforce/ and the save hook
  hook install|uninstall|status    Manage the tk post-write hook for this project
  test [--prompt "<text>"]         Run an end-to-end test worker to verify SCION Hub & worker execution

Dispatch:
  on-save <id> [--event <e>]       Handle one ticket save (called by the hook)
  sync [dir]                       Catch up on saves the hook missed (hand edits, git pull,
                                   worker reports), flag dead workers, start queued tickets
  dispatch <id>                    Start a verified worker for one opted-in ticket now

Workers:
  status                           Save hook, provider health and workers for this project
  list | ps                        List all tracked workers across projects
  feedback <id> "<msg>"            Add a review note, remove waiting-for-review, wake the worker
  attach <id>                      Attach interactively to worker <id>
  pause <id>                       Pause worker <id>
  logs [<id>]                      View task force or worker logs (including .gz)
  brief <id>                       View the persisted worker brief for <id>
  trace [<id>]                     Inspect OpenTelemetry trace spans (filtered by ticket <id>)
  gc [--force]                     Delete workers of tickets closed > 5 days; purge logs > 30 days
  version | help

Opt-in model: only tickets YOU tagged `taskforce` (tags.claim) are picked up; the task force
never adds that tag itself. A ticket moves to in_progress only after its worker is verified running.
"""


_HOOK_HINT = "Ticket saves now start workers; run `tk scion-taskforce hook install` once, then `sync` to catch up."
REMOVED_COMMANDS = {
    "start": _HOOK_HINT,
    "restart": _HOOK_HINT,
    "server": _HOOK_HINT,
    "watch": _HOOK_HINT,
    "project": "Each project uses its own save hook (`tk scion-taskforce hook install`); nothing to register.",
    "stop": "To stop a worker, use `tk scion-taskforce pause <id>` or close its ticket; `hook uninstall` stops dispatch.",
}


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
    for proj_str in known_projects(load_state()):
        proj_p = Path(proj_str)
        t_path = resolve_ticket_path(proj_p, ticket_id)
        if t_path:
            return proj_p, t_path
    raise ValueError(f"Ticket {ticket_id!r} not found in {default_project} or projects with workers.")


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


def _detect_default_gcp_project() -> str:
    env_proj = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")
    if env_proj:
        return env_proj
    try:
        proc = subprocess.run(
            ["gcloud", "config", "get-value", "project"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except Exception:
        pass
    return "gemini-demo-project-4242"


def _prompt_user(prompt: str, default: str) -> str:
    try:
        val = input(f"{prompt} [{default}]: ").strip()
        return val if val else default
    except (EOFError, KeyboardInterrupt):
        print()
        return default


def _ensure_runtime_project(project_dir: Path, explicit_config: str | None = None, dry_run: bool = False) -> None:
    """Register the project folder with the runtime once (Scion: link it to the Hub).

    Only `init` calls this; dispatch never creates runtime/Hub projects.
    Best effort: a failure is reported but never aborts the calling command.
    """
    try:
        cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
        res = get_provider(cfg, dry_run=dry_run).ensure_project_registered(str(project_dir))
    except Exception as exc:  # noqa: BLE001 - registration must not break init
        print(f"⚠️  Scion Hub: could not check project link: {exc}")
        return
    print(f"{'🔗' if res.ok else '⚠️ '} Scion Hub: {res.message}")


def cmd_test(args: list[str], project_dir: Path) -> int:
    """Run an end-to-end test worker to verify SCION Hub & worker execution."""
    cfg = load_config(project_dir=project_dir)
    provider_cfg = cfg.get("provider", {})
    harness = str(provider_cfg.get("harness_config", "claude") or "claude")
    model = str(provider_cfg.get("model", "") or "").strip()
    binary = str(provider_cfg.get("binary", "scion") or "scion")

    prompt = next((args[i + 1] for i, a in enumerate(args) if a in ("--prompt", "-p") and i + 1 < len(args)), None)
    if not prompt:
        prompt = (
            "Write a short markdown file called poem.md with a 4-line poem about the latest "
            "Google Gemini model. Save poem.md directly in the current repository workspace directory "
            "and complete your job."
        )

    test_id = f"test-worker-{int(time.time()) % 10000:04d}"
    target_file = project_dir / "poem.md"

    print("=" * 60)
    print("🧪 Running SCION Task Force Test Worker")
    print("=" * 60)
    print(f"• Worker ID:   `{test_id}`")
    print(f"• Project Dir: `{project_dir}`")
    print(f"• Harness:     `{harness}` (Model: `{model}`)")
    print(f"• Target File: `{target_file.name}`")
    print("-" * 60)

    if target_file.is_file():
        target_file.unlink()

    provider = get_provider(cfg, dry_run=False)
    pre = provider.preflight(str(project_dir))
    if not pre.ok:
        print(f"❌ Provider preflight failed: {pre.message}", file=sys.stderr)
        return 1

    print("🚀 Launching test worker via SCION Hub...")
    cmd = [
        binary,
        "--project",
        str(project_dir),
        "start",
        test_id,
        prompt,
        "-w",
        str(project_dir),
        "--enable-telemetry",
        "--non-interactive",
    ]
    if (project_dir / ".scion" / "templates" / "taskforce-worker").is_dir():
        cmd.extend(["-t", "taskforce-worker"])
    if harness:
        cmd.extend(["--harness-config", harness])
    if model and model.lower() not in ("default", ""):
        cmd.extend(["--model", model])
    for extra in provider_cfg.get("extra_start_args", []):
        cmd.append(str(extra))

    env = os.environ.copy()
    if "GOOGLE_CLOUD_REGION" not in env:
        region = env.get("GOOGLE_CLOUD_LOCATION") or env.get("VERTEX_LOCATION") or ("us-east5" if harness == "claude" else "us-central1")
        env["GOOGLE_CLOUD_REGION"] = region
        env["GOOGLE_CLOUD_LOCATION"] = region

    launch_res = subprocess.run(cmd, cwd=str(project_dir), env=env, capture_output=True, text=True)
    if launch_res.returncode != 0:
        print(f"❌ Failed to launch test worker:\n{launch_res.stderr or launch_res.stdout}", file=sys.stderr)
        return 1

    print(f"✅ Test worker '{test_id}' started on SCION Hub!")
    provider.post_spawn(str(project_dir), test_id, timeout_seconds=15)
    print("⏳ Waiting for worker to write poem.md (polling up to 90s)...")

    start_t = time.time()
    found = False
    while time.time() - start_t < 90:
        if target_file.is_file() and target_file.stat().st_size > 0:
            found = True
            break
        candidate_paths = [
            project_dir / ".scion" / "agents" / test_id / "workspace" / "poem.md",
        ]
        hub_configs = Path.home() / ".scion" / "project-configs"
        if hub_configs.is_dir():
            candidate_paths.extend(hub_configs.glob(f"*/.scion/agents/{test_id}/workspace/poem.md"))

        for candidate in candidate_paths:
            if candidate.is_file() and candidate.stat().st_size > 0:
                import shutil
                shutil.copy2(candidate, target_file)
                found = True
                break
        if found:
            break
        print(".", end="", flush=True)
        time.sleep(2.0)
    print()

    if not found:
        print("⚠️ Test worker did not produce poem.md within 90s.")
        print("   Capturing agent terminal output...")
        look_proc = subprocess.run(
            [binary, "--non-interactive", "--project", str(project_dir), "look", test_id],
            capture_output=True,
            text=True,
        )
        if look_proc.stdout:
            print(look_proc.stdout[:800])
        subprocess.run(
            [binary, "--non-interactive", "--project", str(project_dir), "delete", test_id, "-y"],
            capture_output=True,
        )
        return 1

    content = target_file.read_text(encoding="utf-8").strip()
    print("🎉 Test worker completed successfully!")
    print("📄 Verified poem.md in local project workspace:")
    print("-" * 60)
    print(content)
    print("-" * 60)

    # Clean up test poem so project working directory remains clean
    if target_file.is_file():
        target_file.unlink()

    print(f"🧹 Cleaning up test worker '{test_id}'...")
    subprocess.run(
        [binary, "--non-interactive", "--project", str(project_dir), "delete", test_id, "-y"],
        capture_output=True,
    )
    print("✅ Test run verified! Your SCION Task Force is fully operational.")
    return 0


def cmd_init(args: list[str], project_dir: Path) -> int:
    global_scope = "--global" in args or "-g" in args
    force = "--force" in args or "-f" in args
    is_interactive = (
        sys.stdin.isatty()
        and not global_scope
        and "--defaults" not in args
        and "--non-interactive" not in args
        and "-y" not in args
    )

    harness = "claude"
    model = ""
    gcp_proj = _detect_default_gcp_project()
    gcp_region = os.environ.get("GOOGLE_CLOUD_REGION") or "us-east5"
    claim_tag = "taskforce"
    review_tag = "waiting-for-review"
    max_concurrent = 1

    if is_interactive:
        print("=" * 60)
        print("🚀 SCION Task Force Setup Wizard")
        print("=" * 60)
        print("Configure your project-level worker template & orchestrator.")
        print("Press [Enter] to accept the recommended default in brackets.\n")

        harness = _prompt_user("1. SCION Harness Engine", "claude")
        model = _prompt_user("2. Default Model (Model Garden / Vertex AI, blank for default)", "")
        gcp_proj = _prompt_user("3. Google Cloud Project ID", gcp_proj)
        gcp_region = _prompt_user("4. Google Cloud Region", gcp_region)
        claim_tag = _prompt_user("5. Task Opt-in Tag", "taskforce")
        max_str = _prompt_user("6. Max Concurrent Workers", "1")
        try:
            max_concurrent = int(max_str)
        except ValueError:
            max_concurrent = 1

        os.environ["GOOGLE_CLOUD_PROJECT"] = gcp_proj
        os.environ["GOOGLE_CLOUD_REGION"] = gcp_region

    scope_desc = "global scope" if global_scope else f"project scope at `{project_dir}`"
    print(f"\n🚀 Initializing SCION Task Force ({scope_desc})...")
    target, archived_count = init_config(
        project_dir=project_dir,
        global_scope=global_scope,
        force=force,
        harness=harness,
        model=model,
        claim_tag=claim_tag,
        review_tag=review_tag,
        max_concurrent=max_concurrent,
    )
    if archived_count > 0:
        print(f"📦 Archived {archived_count} existing configuration/prompt file(s) with timestamped .old suffixes.")
    print("📁 Created/Updated configuration directory & templates:")
    print(f"   • Config:   `{target}`")
    print(f"   • Template: `{project_dir / '.scion' / 'templates' / 'taskforce-worker'}` (harness={harness}, model={model})")
    print(f"   • Brief:    `{target.parent / 'prompt.md'}`")
    if not global_scope:
        _ensure_runtime_project(project_dir)
        hook = install_hook(project_dir)
        print(f"🪝 Save hook:  `{hook}` (ticket saves now trigger the task force)")
    print("✅ Initialization successful! Tag a ready ticket `taskforce` to hand it to the task force.")

    if is_interactive:
        try:
            ans = input("\n🧪 Run a quick test worker now? (create poem.md about Gemini) [Y/n]: ").strip().lower()
            if ans in ("", "y", "yes"):
                return cmd_test([], project_dir)
        except (EOFError, KeyboardInterrupt):
            print()

    return 0



def cmd_uninit(args: list[str], project_dir: Path) -> int:
    global_scope = "--global" in args or "-g" in args
    scope_desc = "global config" if global_scope else f"project directory `{project_dir}`"
    print(f"🗑️ Uninitializing SCION Task Force for {scope_desc}...")
    success, path = uninit_config(project_dir=project_dir, global_scope=global_scope)
    if not global_scope and uninstall_hook(project_dir):
        print(f"ℹ️ Removed save hook `{hook_path(project_dir)}`.")
    if success:
        print(f"✅ Successfully removed `{path}`.")
    else:
        print(f"ℹ️ No SCION task force configuration found at `{path}`.")
    return 0


def cmd_hook(args: list[str], project_dir: Path) -> int:
    action = args[0] if args else "status"
    if action == "install":
        print(f"🪝 Installed save hook: {install_hook(project_dir)}")
        return 0
    if action in ("uninstall", "remove", "rm"):
        removed = uninstall_hook(project_dir)
        print("🗑️ Removed save hook." if removed else "ℹ️ No save hook installed.")
        return 0
    if action == "status":
        target = hook_path(project_dir)
        print(f"{'✅ installed' if target.exists() else '❌ not installed'}: {target}")
        return 0
    print(f"Unknown hook action: {action} (use install|uninstall|status)", file=sys.stderr)
    return 1


def cmd_on_save(args: list[str], project_dir: Path, explicit_config: str | None, dry_run: bool) -> int:
    ticket_id = next((a for a in args if not a.startswith("-")), None)
    event = next((args[i + 1] for i, a in enumerate(args) if a == "--event" and i + 1 < len(args)), "")
    if not ticket_id:
        print("Usage: tk scion-taskforce on-save <id> [--event <event>]", file=sys.stderr)
        return 1
    summary = on_save(project_dir, ticket_id, event=event, explicit_config=explicit_config, dry_run=dry_run)
    print(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] on-save {event or '-'}: {summary}")
    return 0


def cmd_sync(args: list[str], project_dir: Path, explicit_config: str | None, dry_run: bool) -> int:
    target = next((a for a in args if not a.startswith("-")), None)
    if not hook_path(Path(target) if target else project_dir).exists():
        print("⚠️  Save hook not installed: ticket saves will not start workers. Run `tk scion-taskforce hook install`.")
    stats = sync_project(Path(target) if target else project_dir, explicit_config=explicit_config, dry_run=dry_run)
    print(
        f"✅ Sync complete: started={stats['started']}, paused={stats['paused']}, "
        f"lost={stats['lost']}, errors={stats['errors']}"
    )
    return 0


def cmd_dispatch(
    args: list[str],
    project_dir: Path,
    explicit_config: str | None,
    dry_run: bool,
) -> int:
    ticket_arg = next((a for a in args if not a.startswith("-")), None)
    if not ticket_arg:
        print("Usage: tk scion-taskforce dispatch <id>   (use `sync` to start all queued tickets)", file=sys.stderr)
        return 1
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    proj, t_path = _find_ticket_across_projects(ticket_arg, project_dir)
    ticket = parse_ticket_file(t_path, project_dir=proj)
    eligible, reason = is_eligible_for_dispatch(ticket, cfg)
    if not eligible:
        claim_tag = str(cfg.get("tags", {}).get("claim", "taskforce"))
        print(f"⏭️  Not dispatching {ticket.id}: {reason}.")
        print(f"   Opt a ticket in with: tk update {ticket.id} --tags <existing>,{claim_tag}")
        return 1
    try:
        ok = dispatch_ticket(proj, ticket, cfg, TelemetryManager(cfg), get_provider(cfg, dry_run=dry_run), load_state())
    except DispatchError as exc:
        print(f"❌ Could not launch a verified worker for '{ticket.id}': {exc}", file=sys.stderr)
        print("   Ticket left untouched. Check the provider runtime (e.g. `podman machine start`).", file=sys.stderr)
        return 1
    if ok:
        print(f"🚀 Dispatched & verified task force worker '{ticket.id}' in {proj}")
        return 0
    print(f"❌ Did not dispatch worker for ticket '{ticket.id}' (see `tk scion-taskforce logs`)", file=sys.stderr)
    return 1


def cmd_list(project_dir: Path, explicit_config: str | None) -> int:
    state = load_state()
    workers: dict[str, dict[str, Any]] = state.get("workers", {})
    if not workers:
        print("No task force workers tracked yet.")
        return 0

    print(f"{'WORKER ID':<14} {'STATE':<10} {'PROVIDER':<10} {'CYCLES':<7} {'PROJECT':<30} {'TRACE ID'}")
    print("-" * 105)
    # states: running | paused | stopped (ticket closed) | error (never verified or pod lost) | deleted
    for w in sorted(workers.values(), key=lambda x: (str(x.get("project_dir", "")), str(x.get("ticket_id", "")))):
        wid = str(w.get("ticket_id", ""))
        st = str(w.get("state", "unknown"))
        prov = str(w.get("provider", "scion"))
        cycles = int(w.get("feedback_cycles", 0))
        proj = str(w.get("project_dir", str(project_dir)))
        trace_id = str(w.get("trace_id", ""))
        print(f"{wid:<14} {st:<10} {prov:<10} {cycles:<7} {proj:<30} {trace_id}")
    return 0


def cmd_status(project_dir: Path, explicit_config: str | None) -> int:
    proj = normalize_project_dir(project_dir)
    hook = hook_path(project_dir)
    print(f"Project:   {proj}")
    print(f"Save hook: {'✅ installed' if hook.exists() else '❌ not installed (run `tk scion-taskforce hook install`)'}")
    state = load_state()
    health = state.get("project_health", {}).get(proj)
    if health:
        label = "ok" if health.get("ok") else f"provider unavailable: {health.get('message', '')}"
        print(f"Provider:  {label} (checked {health.get('checked_at', '?')})")
    mine = [w for w in state.get("workers", {}).values() if w.get("project_dir") == proj]
    print(f"Workers:   {len(mine)}")
    for w in sorted(mine, key=lambda x: str(x.get("ticket_id", ""))):
        print(f"  {str(w.get('ticket_id', '')):<14} {str(w.get('state', 'unknown')):<10}")
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
        lines = telemetry.read_logs(limit=200)
        if not lines:
            print(f"No task force logs found at {telemetry.log_file}")
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
    projects = known_projects(state)
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

    if subcmd == "test":
        return cmd_test(subargs, project_dir)

    if subcmd == "uninit":
        return cmd_uninit(subargs, project_dir)

    if subcmd == "hook":
        return cmd_hook(subargs, project_dir)

    if subcmd == "on-save":
        return cmd_on_save(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "sync":
        return cmd_sync(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "status":
        return cmd_status(project_dir, explicit_config)

    # Commands that write worker state share the per-project lock with the background hook.
    # shortcut: locks only the current project; lock per touched project if cross-project writes race.
    writers = {"dispatch": cmd_dispatch, "feedback": cmd_feedback, "pause": cmd_pause, "gc": cmd_gc}
    if subcmd in writers:
        with project_lock(Path(normalize_project_dir(project_dir))):
            return writers[subcmd](subargs, project_dir, explicit_config, dry_run)

    if subcmd in ("list", "ps"):
        return cmd_list(project_dir, explicit_config)

    if subcmd == "attach":
        return cmd_attach(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "logs":
        return cmd_logs(subargs, project_dir, explicit_config)

    if subcmd == "brief":
        return cmd_brief(subargs, project_dir, explicit_config)

    if subcmd == "trace":
        return cmd_trace(subargs, project_dir, explicit_config)

    if subcmd in REMOVED_COMMANDS:
        print(f"`{subcmd}` was removed: the polling daemon is gone. {REMOVED_COMMANDS[subcmd]}", file=sys.stderr)
        return 2

    print(f"Unknown subcommand: {subcmd!r}. Run 'tk scion-taskforce help' for usage.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
