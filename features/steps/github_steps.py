"""Step definitions for the GitHub import plugin (plugins/github) with a stubbed `gh`."""

import json
import re
import tempfile
from pathlib import Path

from behave import given, then, use_step_matcher

use_step_matcher("re")


@given(r'a fake gh CLI that returns these issues:?')
def step_fake_gh_issues(context):
    """Install a `gh` stub on PATH: auth succeeds, `issue list` prints the docstring JSON."""
    json.loads(context.text)  # fail early on malformed fixtures
    if not hasattr(context, 'plugin_dir'):
        context.plugin_dir = tempfile.mkdtemp(prefix='ticket_plugins_')
    fixture = Path(context.plugin_dir) / 'gh-issues.json'
    fixture.write_text(context.text)
    gh = Path(context.plugin_dir) / 'gh'
    gh.write_text(f'''#!/usr/bin/env bash
case "$1 $2" in
    "auth status") exit 0 ;;
    "issue list") cat "{fixture}" ;;
    *) echo "[]" ;;
esac
''')
    gh.chmod(0o755)
    # Pin the plugin under test: an installed tk-github elsewhere on PATH would otherwise win.
    plugin = Path(context.plugin_dir) / 'tk-github'
    if not plugin.exists():
        plugin.symlink_to(Path(context.project_dir) / 'plugins' / 'github' / 'ticket-github')


def _imported_ticket(context, ref):
    tickets_dir = Path(context.test_dir) / '.tickets'
    for f in tickets_dir.glob('*.md'):
        content = f.read_text()
        if re.search(rf'^external[-_]ref: {re.escape(ref)}$', content, re.MULTILINE):
            return content
    raise AssertionError(f"No ticket with external ref {ref} in {tickets_dir}")


@then(r'the ticket imported from "(?P<ref>[^"]+)" should have title "(?P<title>[^"]+)"')
def step_imported_title(context, ref, title):
    content = _imported_ticket(context, ref)
    titles = re.findall(r'^# (.*)$', content, re.MULTILINE)
    assert titles and titles[0] == title, f"Expected title {title!r}, got {titles[:1]}\n{content}"


@then(r'the ticket imported from "(?P<ref>[^"]+)" should have field "(?P<field>[^"]+)" with value "(?P<value>[^"]+)"')
def step_imported_field(context, ref, field, value):
    content = _imported_ticket(context, ref)
    m = re.search(rf'^{re.escape(field)}: (.*)$', content, re.MULTILINE)
    assert m and m.group(1) == value, f"Expected {field}: {value}, got {m.group(1) if m else None}\n{content}"


@then(r'the ticket imported from "(?P<ref>[^"]+)" should contain "(?P<text>[^"]+)"')
def step_imported_contains(context, ref, text):
    content = _imported_ticket(context, ref)
    assert text in content, f"Expected {text!r} in ticket\n{content}"
