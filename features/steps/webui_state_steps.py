"""Step definitions comparing Web UI blocked/ready state with core tk ready/blocked."""

import os
import subprocess
from pathlib import Path

from behave import then, use_step_matcher

use_step_matcher("re")


def _tk_ids(context, cmd):
    env = os.environ.copy()
    env['TICKETS_DIR'] = str(Path(context.test_dir) / '.tickets')
    out = subprocess.run(
        [str(Path(context.project_dir) / 'ticket'), cmd],
        cwd=context.test_dir, env=env, capture_output=True, text=True, stdin=subprocess.DEVNULL, check=True,
    ).stdout
    return sorted(line.split()[0] for line in out.splitlines() if line.strip())


def _webui_tickets(context):
    from tk_webui import tk_cli

    return tk_cli.get_all_tickets(context.test_dir)


@then(r'the web UI ready and blocked tickets should match tk ready and tk blocked')
def step_webui_matches_core(context):
    tickets = _webui_tickets(context)
    ui_ready = sorted(t.id for t in tickets if t.status in ('open', 'in_progress') and not t.is_blocked)
    ui_blocked = sorted(t.id for t in tickets if t.is_blocked)
    core_ready, core_blocked = _tk_ids(context, 'ready'), _tk_ids(context, 'blocked')
    assert ui_ready == core_ready, f"ready: web UI {ui_ready} != tk {core_ready}"
    assert ui_blocked == core_blocked, f"blocked: web UI {ui_blocked} != tk {core_blocked}"
    context.webui_by_id = {t.id: t for t in tickets}


@then(r'the web UI ready tickets should be "(?P<ids>[^"]*)"')
def step_webui_ready_ids(context, ids):
    tickets = _webui_tickets(context)
    got = sorted(t.id for t in tickets if t.status in ('open', 'in_progress') and not t.is_blocked)
    assert got == sorted(ids.split(',')), f"web UI ready: {got}"


@then(r'the web UI blocked tickets should be "(?P<ids>[^"]*)"')
def step_webui_blocked_ids(context, ids):
    got = sorted(t.id for t in _webui_tickets(context) if t.is_blocked)
    assert got == sorted(ids.split(',')), f"web UI blocked: {got}"


@then(r'the web UI should show "(?P<ticket_id>[^"]*)" blocked by "(?P<blockers>[^"]*)"')
def step_webui_blocked_by(context, ticket_id, blockers):
    ticket = {t.id: t for t in _webui_tickets(context)}[ticket_id]
    assert ticket.blocked_by == blockers.split(','), f"{ticket_id} blocked_by: {ticket.blocked_by}"
