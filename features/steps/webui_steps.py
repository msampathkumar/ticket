"""Step definitions for the Web UI tk CLI wrapper (tk_webui/tk_cli.py)."""

from pathlib import Path

from behave import then, use_step_matcher, when

use_step_matcher("re")


def _tk_cli(context):
    from tk_webui import tk_cli

    tk_cli.TK_BIN = str(Path(context.project_dir) / 'ticket')
    return tk_cli


def _record(context, ok, message):
    context.returncode = 0 if ok else 1
    context.stdout = message if ok else ''
    context.stderr = '' if ok else message


@when(r'I create a ticket via the web UI with title "(?P<title>[^"]*)"(?: and description "(?P<description>[^"]*)")?')
def step_webui_create(context, title, description=None):
    tk_cli = _tk_cli(context)
    ok, message = tk_cli.create_ticket_cli(context.test_dir, title, description=description)
    _record(context, ok, message)
    if ok:
        context.last_created_id = message


@when(r'I add dependency "(?P<dep_id>[^"]*)" to "(?P<ticket_id>[^"]*)" via the web UI')
def step_webui_dep(context, dep_id, ticket_id):
    ok, message = _tk_cli(context).add_dep_cli(context.test_dir, ticket_id, dep_id)
    _record(context, ok, message)


@when(r'I add note "(?P<note>[^"]*)" to "(?P<ticket_id>[^"]*)" via the web UI')
def step_webui_note(context, note, ticket_id):
    ok, message = _tk_cli(context).add_note_cli(context.test_dir, ticket_id, note)
    _record(context, ok, message)


@then(r'the tickets directory should contain (?P<count>\d+) tickets?')
def step_ticket_count(context, count):
    files = list((Path(context.test_dir) / '.tickets').glob('*.md'))
    assert len(files) == int(count), f"Expected {count} tickets, found {[f.name for f in files]}"
