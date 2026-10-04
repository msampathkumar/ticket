"""Command-line interface for tk-scion-taskforce."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from tk_scion_taskforce import __version__
from tk_scion_taskforce.config import (
    WORKER_TEMPLATE,
    ConfigError,
    init_config,
    load_config,
    project_config_path,
    resolve_config_path,
    uninit_config,
)
from tk_scion_taskforce.events import (
    collect_reports,
    dispatch_now,
    hook_path,
    install_hook,
    on_save,
    project_agents,
    remove_project_workers,
    sync_project,
    uninstall_hook,
)
from tk_scion_taskforce.providers.scion import ScionProvider
from tk_scion_taskforce.roles import (
    DEFAULT_ROLES,
    UPSTREAM_REF,
    RoleInstallError,
    install_roles,
    installed_roles,
)
from tk_scion_taskforce.state import StateError, known_projects, load_state, normalize_project_dir, state_lock
from tk_scion_taskforce.telemetry import TelemetryManager, new_trace_id, project_slug
from tk_scion_taskforce.tickets import find_tk_binary, parse_ticket_file, resolve_ticket_path
from tk_scion_taskforce.wizard import (
    WizardAbort,
    default_harness,
    ensure_project_initialized,
    installed_harnesses,
    run_wizard,
)
from tk_scion_taskforce.workers import (
    _worker_key,
    git_mode,
    pause_worker_for_ticket,
    privacy_level,
    project_lock,
    run_gc,
    send_feedback_to_worker,
    tags,
)

HELP_TEXT = """tk-scion-taskforce - Autonomous SCION task force orchestrator plugin for tk

Usage:
  tk scion-taskforce [--config <path>] [--dry-run] <subcommand> [args...]

`init` installs a tk post-write hook. Every ticket save (CLI or Web UI) runs `on-save <id>`
in the background. For a ticket YOU tagged `taskforce`:
- ready (open, deps closed): status note, then a Scion worker starts (or the ticket queues)
- note added while its worker is active: forwarded to the worker
- worker reports back (`waiting-for-review`): worker paused, next queued ticket starts
- ticket closed: worker stopped, next queued ticket starts
- tag removed, `no-taskforce` added or ticket file deleted: worker stopped and deleted (branch kept)
`gc` deletes the workers of tickets closed more than 5 days ago. A `role:<name>` tag runs the
worker on the role template `tk-<name>` (see `templates`).

Setup:
  init [--global] [--force] [--defaults|--interactive]
                                   tk/scion init if needed; setup wizard: config, template, Hub link, save hook
  uninit [--global] [--yes]        Stop and delete this project's workers (branches kept), then remove
                                   .scion-taskforce/, the worker template and the save hook; asks first unless --yes
  hook install|uninstall|status    Manage the tk post-write hook for this project
  test [--timeout <s>] [--keep]    Create a ticket tagged init+taskforce, wait for its worker to report back
  templates install [<role>...] [--force] [--from <dir>] [--ref <sha>]
                                   Install agent-team role templates (default set) into .scion/templates/,
                                   skills vendored, pinned to a commit; --from uses a local <owner>/<repo>/ mirror
  templates list                   Installed role templates and their sources

Dispatch:
  on-save <id> [--event <e>]       Handle one ticket save (called by the hook)
  sync [dir]                       Catch up on saves the hook missed (hand edits, git pull,
                                   worker reports), flag dead workers, start queued tickets
  dispatch <id>                    Start a worker for one ready, opted-in ticket now (ignores the worker limit)

Workers:
  status                           Settings, save hook, provider health, workers, what needs you and
                                   the automatic actions taken for this project
  list | ps                        List all tracked workers across projects
  feedback <id> "<msg>"            Wake the ticket's active worker with a review note, remove waiting-for-review
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
# deprecated: daemon-era commands, kept only to print a migration hint; remove after 2027-01-01
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
    return ""


def _ensure_runtime_project(project_dir: Path, explicit_config: str | None = None, dry_run: bool = False) -> None:
    """Register the project folder with the runtime once (Scion: link it to the Hub).

    Only `init` calls this; dispatch never creates runtime/Hub projects.
    Best effort: a failure is reported but never aborts the calling command.
    """
    try:
        cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
        res = ScionProvider(cfg, dry_run=dry_run).ensure_project_registered(str(project_dir))
    except Exception as exc:  # noqa: BLE001 - registration must not break init
        print(f"⚠️  Scion Hub: could not check project link: {exc}")
        return
    print(f"{'🔗' if res.ok else '⚠️ '} Scion Hub: {res.message}")


SMOKE_TITLE = "Task force check: report your setup"
SMOKE_BODY = """Created by `tk scion-taskforce test` to verify the task force end to end. Do not change any file except this ticket.

1. Add a note to this ticket with: the harness and model you run on, whether the workspace is a git repository, and the output of `ls | head -10`. Do not change git state.
2. Add the `{review_tag}` tag to this ticket, then stop.
"""


def _flag_value(args: list[str], names: tuple[str, ...], default: str) -> str:
    return next((args[i + 1] for i, a in enumerate(args) if a in names and i + 1 < len(args)), default)


def cmd_test(args: list[str], project_dir: Path) -> int:
    if "--raw" in args:
        # deprecated: `test --raw` launched a worker outside the real dispatch path; remove after 2027-01-01
        print("`--raw` was removed; `tk scion-taskforce test` verifies end to end through a ticket.", file=sys.stderr)
        return 2
    return _test_via_ticket(args, project_dir)


def _test_via_ticket(args: list[str], project_dir: Path) -> int:
    """Create a tk ticket tagged `init` + the claim tag and wait until its worker reports back.

    Exercises the whole pipeline: tk save hook -> on-save -> dispatch -> worker (project template)
    -> report merged back as a note + the review tag. Closes the ticket afterwards unless --keep.
    """
    claim_tag, _, review_tag = tags(load_config(project_dir=project_dir))
    timeout = int(_flag_value(args, ("--timeout",), "600"))
    if not hook_path(project_dir).exists():
        print("❌ Save hook not installed; run `tk scion-taskforce init` (or `hook install`) first.", file=sys.stderr)
        return 1
    tk_bin = find_tk_binary(project_dir)
    if not tk_bin:
        print("❌ `tk` not found on PATH.", file=sys.stderr)
        return 1

    env = {**os.environ, "TICKETS_DIR": str(project_dir / ".tickets")}
    created = subprocess.run(
        [tk_bin, "create", SMOKE_TITLE, "-d", SMOKE_BODY.format(review_tag=review_tag), "--tags", f"init,{claim_tag}"],
        cwd=str(project_dir), env=env, capture_output=True, text=True,
    )
    tid = created.stdout.strip().splitlines()[-1] if created.returncode == 0 and created.stdout.strip() else ""
    if not tid:
        print(f"❌ Could not create the check ticket: {(created.stderr or created.stdout).strip()}", file=sys.stderr)
        return 1
    print(f"🧪 Created ticket {tid} (tags: init, {claim_tag}); the save hook hands it to the task force.")
    print(f"⏳ Waiting up to {timeout}s for the worker to report back (Ctrl-C stops waiting; the worker keeps going)...")

    seen = 0
    deadline = time.time() + timeout
    try:
        while True:
            collect_reports(project_dir)
            t_path = resolve_ticket_path(project_dir, tid)
            ticket = parse_ticket_file(t_path, project_dir=project_dir) if t_path else None
            if ticket is None:
                print(f"❌ Ticket {tid} disappeared.", file=sys.stderr)
                return 1
            for _, body in ticket.notes[seen:]:
                print(f"   • {body.splitlines()[0][:160]}")
            seen = len(ticket.notes)
            last = ticket.notes[-1][1] if ticket.notes else ""
            if review_tag in ticket.tags:
                break
            if "could not start a Scion worker" in last:
                print(f"❌ Dispatch failed; see the note above and `tk scion-taskforce logs`. Ticket {tid} left open.")
                return 1
            if time.time() >= deadline:
                print(f"⌛ Timed out. Inspect with `tk scion-taskforce attach {tid}` or `logs {tid}`; ticket {tid} left open.")
                return 1
            time.sleep(min(10, max(1, deadline - time.time())))
    except KeyboardInterrupt:
        print(f"\nStopped waiting. Check later with `tk show {tid}` / `tk scion-taskforce sync`.")
        return 130

    print(f"✅ Worker reported back on {tid}: the task force works end to end.")
    if "--keep" in args:
        print(f"   Ticket left open (--keep). Close it with `tk close {tid}` to stop its worker.")
    else:
        subprocess.run([tk_bin, "close", tid], cwd=str(project_dir), env=env, capture_output=True, text=True)
        print(f"   Closed {tid}; its worker is stopped. The ticket keeps the worker's report.")
    return 0


def cmd_init(args: list[str], project_dir: Path) -> int:
    global_scope = "--global" in args or "-g" in args
    force = "--force" in args or "-f" in args
    is_interactive = not global_scope and (
        "--interactive" in args
        or (
            sys.stdin.isatty()
            and "--defaults" not in args
            and "--non-interactive" not in args
            and "-y" not in args
        )
    )

    binary = str(load_config(project_dir=project_dir).get("provider", {}).get("binary", "scion") or "scion")
    installed = [] if global_scope else installed_harnesses(binary)
    answers: dict[str, Any] = {
        "harness": default_harness(installed),
        "model": "",
        "gcp_project": "",  # non-interactive: inherit GOOGLE_CLOUD_PROJECT from the shell
        "gcp_region": "",  # non-interactive: keep the shell's region (or the harness fallback)
        "claim_tag": "taskforce",
        "max_concurrent": 1,
        "privacy": "confidential",
        "roles": "none",  # non-interactive: no download; `templates install` adds roles later
    }
    if is_interactive:
        answers["gcp_project"] = _detect_default_gcp_project()
        try:
            answers = run_wizard(answers, installed)
        except WizardAbort:
            print("\nSetup cancelled; nothing was changed.")
            return 1

    if not global_scope:
        print("\n🔎 Checking project setup...")
        ensure_project_initialized(project_dir, binary)

    scope_desc = "global scope" if global_scope else f"project scope at `{project_dir}`"
    print(f"\n🚀 Initializing SCION Task Force ({scope_desc})...")
    # Re-running init keeps an existing config: only the wizard (or --force) changes its values.
    write_answers = not global_scope and (is_interactive or force or not project_config_path(project_dir).exists())
    target, action = init_config(
        project_dir=project_dir,
        global_scope=global_scope,
        force=force,
        answers=answers if write_answers else None,
    )
    note = {
        "created": "created",
        "updated": "updated the wizard's settings, kept your other values",
        "kept": "kept your existing values; `--force` starts over",
    }[action]
    print(f"📁 Config:   `{target}` ({note})")
    if not global_scope:
        prov = load_config(project_dir=project_dir)["provider"]
        harness, model = prov.get("harness_config") or "default", prov.get("model") or "harness default"
        print(f"   Template: `{project_dir / '.scion' / 'templates' / WORKER_TEMPLATE}` (harness={harness}, model={model})")
        _ensure_runtime_project(project_dir)
        hook = install_hook(project_dir)
        print(f"🪝 Save hook:  `{hook}` (ticket saves now trigger the task force)")
        if is_interactive and answers.get("roles", "none") != "none":
            chosen = None if answers["roles"] == "recommended" else [r.strip() for r in answers["roles"].split(",")]
            _install_roles_report(project_dir, chosen, str(answers.get("privacy", "confidential")))
    print(f"✅ Initialization successful! Tag a ready ticket `{answers['claim_tag']}` to hand it to the task force.")

    if is_interactive:
        try:
            ans = input(
                f"\n🧪 Verify now? Creates a tk ticket tagged `init,{answers['claim_tag']}` and waits for a Scion worker"
                " to finish it (usually a few minutes) [Y/n]: "
            ).strip().lower()
            if ans in ("", "y", "yes"):
                return cmd_test([], project_dir)
        except (EOFError, KeyboardInterrupt):
            print()

    return 0



def _install_roles_report(
    project_dir: Path, roles: list[str] | None, privacy: str, mirror: Path | None = None,
    ref: str = UPSTREAM_REF, force: bool = False,
) -> int:
    print(f"🧩 Role templates: fetching {', '.join(roles or DEFAULT_ROLES)} ({'local mirror' if mirror else 'GitHub'})...")
    try:
        results = install_roles(project_dir, roles, privacy=privacy, mirror=mirror, ref=ref, force=force)
    except RoleInstallError as exc:
        print(f"⚠️  Role templates not installed: {exc}\n   Retry with `tk scion-taskforce templates install`.")
        return 1
    for r in results:
        if r.action == "kept":
            print(f"   = {r.template_dir.name}: kept (use --force to regenerate)")
            continue
        dropped = f"; dropped: {', '.join(r.dropped)}" if r.dropped else ""
        print(f"   ✓ {r.template_dir.name}: {r.action}, {len(r.skills)} skill(s) vendored{dropped}")
    print("   Sources and licences: UPSTREAM.md in each folder. Tag a ticket `role:<name>` to use one.")
    return 0


def cmd_templates(args: list[str], project_dir: Path, explicit_config: str | None) -> int:
    action = args[0] if args else "list"
    if action == "list":
        found = installed_roles(project_dir)
        if not found:
            print("No role templates installed. Run `tk scion-taskforce templates install`.")
        for role, source in found:
            print(f"  {role:<18} tk-{role:<20} {source}")
        print(f"Default set: {', '.join(DEFAULT_ROLES)}")
        return 0
    if action != "install":
        print("Usage: tk scion-taskforce templates install [<role>...] [--force] [--from <dir>] [--ref <sha>] | list",
              file=sys.stderr)
        return 1
    rest = args[1:]
    value_flags = ("--from", "--ref")
    roles = [a for i, a in enumerate(rest) if not a.startswith("-") and (i == 0 or rest[i - 1] not in value_flags)]
    mirror = _flag_value(rest, ("--from",), "")
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    return _install_roles_report(
        project_dir, roles or None, privacy_level(cfg),
        mirror=Path(mirror).expanduser().resolve() if mirror else None,
        ref=_flag_value(rest, ("--ref",), UPSTREAM_REF),
        force="--force" in rest or "-f" in rest,
    )


def cmd_uninit(args: list[str], project_dir: Path, explicit_config: str | None, dry_run: bool) -> int:
    global_scope = "--global" in args or "-g" in args
    scope_desc = "global config" if global_scope else f"project directory `{project_dir}`"
    agents = [] if global_scope else project_agents(project_dir)
    if agents:
        print(f"This stops and deletes {len(agents)} Scion worker(s) of this project (branches are kept): {', '.join(agents)}")
        if "--yes" not in args and "-y" not in args:
            try:
                answer = input("Continue? [y/N]: ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print("Aborted; nothing was changed. Re-run with --yes to skip this question.")
                return 1
    print(f"🗑️ Uninitializing SCION Task Force for {scope_desc}...")
    if agents:
        removed = remove_project_workers(project_dir, explicit_config=explicit_config, dry_run=dry_run)
        print(f"ℹ️ Stopped and deleted {removed} worker(s).")
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
    proj, t_path = _find_ticket_across_projects(ticket_arg, project_dir)
    tid = parse_ticket_file(t_path, project_dir=proj).id
    ok, reason = dispatch_now(proj, t_path, explicit_config=explicit_config, dry_run=dry_run)
    if ok:
        print(f"🚀 Dispatched & verified task force worker '{tid}' in {proj}")
        return 0
    print(f"❌ Not dispatching {tid}: {reason}", file=sys.stderr)
    if "opt-in tag" in reason:
        claim_tag = tags(load_config(project_dir=proj, explicit_config=explicit_config))[0]
        print(f"   Opt a ticket in with: tk update {tid} --tags <existing>,{claim_tag}", file=sys.stderr)
    return 1


def cmd_list(project_dir: Path, explicit_config: str | None) -> int:
    state = load_state()
    workers: dict[str, dict[str, Any]] = state.get("workers", {})
    if not workers:
        print("No task force workers tracked yet.")
        return 0

    print(f"{'WORKER ID':<14} {'STATE':<10} {'CYCLES':<7} {'PROJECT':<30} {'TRACE ID'}")
    print("-" * 94)
    # states: running | paused | stopped (ticket closed) | error (never verified or pod lost) | deleted
    for w in sorted(workers.values(), key=lambda x: (str(x.get("project_dir", "")), str(x.get("ticket_id", "")))):
        wid = str(w.get("ticket_id", ""))
        st = str(w.get("state", "unknown"))
        cycles = int(w.get("feedback_cycles", 0))
        proj = str(w.get("project_dir", str(project_dir)))
        trace_id = str(w.get("trace_id", ""))
        print(f"{wid:<14} {st:<10} {cycles:<7} {proj:<30} {trace_id}")
    return 0


def cmd_status(project_dir: Path, explicit_config: str | None) -> int:
    proj = normalize_project_dir(project_dir)
    cfg = load_config(project_dir=project_dir, explicit_config=explicit_config)
    hook = hook_path(project_dir)
    roles = ", ".join(r for r, _ in installed_roles(project_dir)) or "none"
    print(f"Project:   {proj}")
    print(f"Settings:  worker.git={git_mode(cfg)}, worker.privacy={privacy_level(cfg)}, roles: {roles}")
    print(f"Save hook: {'✅ installed' if hook.exists() else '❌ not installed (run `tk scion-taskforce hook install`)'}")
    state = load_state()
    needs: list[str] = []
    health = state.get("project_health", {}).get(proj)
    if health:
        label = "ok" if health.get("ok") else "unavailable"
        print(f"Provider:  {label} (checked {health.get('checked_at', '?')})")
        if not health.get("ok"):
            needs.append(str(health.get("message", "")).splitlines()[0][:200])
    if privacy_level(cfg) == "confidential":
        endpoint = ScionProvider(cfg).hub_endpoint(proj)
        if endpoint and not re.match(r"^https?://(127\.0\.0\.1|localhost|\[::1\])(:|/|$)", endpoint):
            needs.append(f"Hub endpoint {endpoint} is not local; this confidential project's prompts go there")
    mine = [w for w in state.get("workers", {}).values() if w.get("project_dir") == proj]
    print(f"Workers:   {len(mine)}")
    for w in sorted(mine, key=lambda x: str(x.get("ticket_id", ""))):
        print(f"  {str(w.get('ticket_id', '')):<14} {str(w.get('state', 'unknown')):<10}")
        if w.get("state") == "error" and w.get("error"):
            needs.append(f"{w.get('ticket_id')}: {str(w['error']).splitlines()[0][:160]}")
    print("Needs you:" + ("" if needs else " nothing"))
    for item in needs:
        print(f"  - {item}")
    actions = _automatic_actions(cfg, proj)
    print("Automatic actions (latest 5):" + ("" if actions else " none"))
    for line in actions[-5:]:
        print(f"  {line}")
    return 0


def _automatic_actions(cfg: dict[str, Any], proj: str) -> list[str]:
    """Log records flagged ``autofix`` for this project, as ``<timestamp> <message>``."""
    out = []
    for raw in TelemetryManager(cfg).read_logs(limit=5000):
        try:
            rec = json.loads(raw)
        except ValueError:
            continue
        attrs = rec.get("attributes") or {}
        if attrs.get("autofix") and attrs.get("project") == proj:
            out.append(f"{rec.get('timestamp', '?')} {rec.get('message', '')}")
    return out


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
    proj, t_path = _find_ticket_across_projects(ticket_id, project_dir)
    ticket = parse_ticket_file(t_path, project_dir=proj)
    cfg = load_config(project_dir=proj, explicit_config=explicit_config)
    state = load_state()

    if ticket.status == "closed":
        print(f"❌ Ticket {ticket.id} is closed; reopen it before sending feedback.", file=sys.stderr)
        return 1
    w_state = state.get("workers", {}).get(_worker_key(proj, ticket.id), {}).get("state")
    if w_state not in ("running", "paused"):
        print(
            f"❌ Ticket {ticket.id} has no active worker (state: {w_state or 'none'}); nothing to wake.\n"
            f"   Add a note with `tk add-note {ticket.id} ...`, or start a worker with "
            f"`tk scion-taskforce dispatch {ticket.id}`.",
            file=sys.stderr,
        )
        return 1

    ok = send_feedback_to_worker(
        project_dir=proj,
        ticket_id=ticket.id,
        feedback_message=feedback_msg,
        config=cfg,
        telemetry=TelemetryManager(cfg),
        provider=ScionProvider(cfg, dry_run=dry_run),
        state=state,
        append_note_to_ticket=True,
    )
    if ok:
        print(f"💬 Feedback added to {ticket.id}, removed waiting-for-review, and woke worker.")
        return 0
    print(
        f"❌ Failed to wake worker {ticket.id}; the ticket was not changed. See `tk scion-taskforce logs {ticket.id}`.",
        file=sys.stderr,
    )
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
    ok = pause_worker_for_ticket(
        project_dir=proj,
        ticket=ticket,
        telemetry=TelemetryManager(cfg),
        provider=ScionProvider(cfg, dry_run=dry_run),
        state=load_state(),
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
    provider = ScionProvider(cfg, dry_run=dry_run)
    w_entry = load_state().get("workers", {}).get(_worker_key(proj, ticket.id), {})
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
        },
    )
    telemetry.log_worker(proj, ticket.id, f"Interactive attach requested: {' '.join(cmd)}", trace_id=trace_id)

    if provider.dry_run:
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
    provider = ScionProvider(cfg, dry_run=dry_run)
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
    try:
        return _main(argv)
    except (StateError, ConfigError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1


def _main(argv: list[str] | None = None) -> int:
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
        return cmd_uninit(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "templates":
        return cmd_templates(subargs, project_dir, explicit_config)

    if subcmd == "hook":
        return cmd_hook(subargs, project_dir)

    if subcmd == "on-save":
        return cmd_on_save(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "sync":
        return cmd_sync(subargs, project_dir, explicit_config, dry_run)

    if subcmd == "status":
        return cmd_status(project_dir, explicit_config)

    if subcmd == "dispatch":  # takes the ticket's project lock itself
        return cmd_dispatch(subargs, project_dir, explicit_config, dry_run)

    # Commands that write worker state share the per-project lock with the background hook, plus the
    # global state-file lock (the state file is shared by all projects).
    writers = {"feedback": cmd_feedback, "pause": cmd_pause, "gc": cmd_gc}
    if subcmd in writers:
        with project_lock(Path(normalize_project_dir(project_dir))), state_lock():
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
