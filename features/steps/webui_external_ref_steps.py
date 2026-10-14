"""Step definitions for Web UI external-ref handling (tk_webui/tk_cli.py)."""

from pathlib import Path

from behave import given, then, use_step_matcher, when

use_step_matcher("re")


def _tk_cli(context):
    from tk_webui import tk_cli

    tk_cli.TK_BIN = str(Path(context.project_dir) / 'ticket')
    return tk_cli


@given(r'ticket "(?P<ticket_id>[^"]*)" has frontmatter line "(?P<line>[^"]*)"')
def step_add_frontmatter_line(context, ticket_id, line):
    path = Path(context.test_dir) / '.tickets' / f'{ticket_id}.md'
    content = path.read_text()
    assert content.startswith('---\n'), f"No frontmatter in {path}"
    path.write_text('---\n' + line + '\n' + content[4:])


@when(r'I set external ref "(?P<ref>[^"]*)" on "(?P<ticket_id>[^"]*)" via the web UI')
def step_webui_set_external_ref(context, ref, ticket_id):
    ok, message = _tk_cli(context).update_ticket_content_cli(context.test_dir, ticket_id, external_ref=ref)
    assert ok, f"update failed: {message}"


@then(r'the web UI should show external ref "(?P<ref>[^"]*)" on "(?P<ticket_id>[^"]*)"')
def step_webui_external_ref(context, ref, ticket_id):
    ticket = _tk_cli(context).parse_ticket_markdown(Path(context.test_dir) / '.tickets' / f'{ticket_id}.md')
    assert ticket is not None, f"Could not parse {ticket_id}"
    assert ticket.external_ref == ref, f"Expected {ref!r}, got {ticket.external_ref!r}"
