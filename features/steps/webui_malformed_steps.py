"""Steps for Web UI resilience to odd or broken ticket frontmatter (tic-r5v9)."""

from pathlib import Path

from behave import given, then, use_step_matcher

use_step_matcher("re")


def _tk_cli(context):
    from tk_webui import tk_cli

    tk_cli.TK_BIN = str(Path(context.project_dir) / 'ticket')
    return tk_cli


@given(r'ticket "(?P<ticket_id>[^"]+)" has raw frontmatter line "(?P<line>[^"]+)"')
def step_raw_frontmatter_line(context, ticket_id, line):
    """Replace (or add) a frontmatter key with a verbatim line, e.g. a YAML flow list."""
    path = Path(context.test_dir) / '.tickets' / f'{ticket_id}.md'
    key = line.split(':', 1)[0]
    lines = path.read_text().split('\n')
    end = lines.index('---', 1)
    front = [ln for ln in lines[1:end] if not ln.startswith(f'{key}:')]
    path.write_text('\n'.join(['---', *front, line, *lines[end:]]))


@given(r'the web UI parser fails on ticket "(?P<ticket_id>[^"]+)"')
def step_parser_fails(context, ticket_id):
    """Make parsing one ticket raise, to exercise the skip-and-log path."""
    tk_cli = _tk_cli(context)
    original = tk_cli.parse_ticket_markdown

    def failing(file_path):
        if Path(file_path).stem == ticket_id:
            raise ValueError(f"simulated parse failure for {ticket_id}")
        return original(file_path)

    tk_cli.parse_ticket_markdown = failing
    context.add_cleanup(setattr, tk_cli, 'parse_ticket_markdown', original)


@then(r'the web UI should show ticket "(?P<ticket_id>[^"]+)" with tags "(?P<tags>[^"]*)"')
def step_webui_tags(context, ticket_id, tags):
    tickets = {t.id: t for t in _tk_cli(context).get_all_tickets(context.test_dir)}
    assert ticket_id in tickets, f"{ticket_id} missing; got {sorted(tickets)}"
    expected = tags.split('|')
    assert tickets[ticket_id].tags == expected, f"tags {tickets[ticket_id].tags!r} != {expected!r}"


@then(r'the API ticket list should (?P<neg>not )?contain ticket "(?P<ticket_id>[^"]+)"')
def step_api_list_has_id(context, neg, ticket_id):
    from urllib.parse import quote

    from fastapi.testclient import TestClient

    from tk_webui.main import app

    _tk_cli(context)
    resp = TestClient(app, base_url="http://127.0.0.1").get(f"/api/tickets?directory={quote(context.test_dir, safe='')}")
    assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text[:300]}"
    ids = [t["id"] for t in resp.json()]
    assert (ticket_id not in ids) if neg else (ticket_id in ids), f"ids: {ids}"
