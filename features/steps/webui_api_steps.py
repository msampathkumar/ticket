"""Black-box HTTP steps for the Web UI REST API (tk_webui/main.py) via FastAPI TestClient."""

import json
import os
import re
from pathlib import Path
from urllib.parse import quote

from behave import given, then, use_step_matcher, when

use_step_matcher("re")


def _expand(context, text):
    """Replace {dir} with the scenario directory (URL-encoded inside query strings)."""
    return text.replace("{dir}", context.test_dir)


def _expand_path(context, path):
    return path.replace("{dir}", quote(context.test_dir, safe=""))


def _client(context):
    if getattr(context, "api_client", None) is None:
        from fastapi.testclient import TestClient

        from tk_webui import tk_cli
        from tk_webui.main import app

        # Use the repo's tk script and keep projects.json (written by both tk_cli and the core
        # script) out of the developer's real state dir.
        saved = (tk_cli.TK_BIN, tk_cli.STATE_DIR, tk_cli.PROJECTS_FILE, os.environ.get("HOME"))

        def restore():
            tk_cli.TK_BIN, tk_cli.STATE_DIR, tk_cli.PROJECTS_FILE, home = saved
            if home is None:
                os.environ.pop("HOME", None)
            else:
                os.environ["HOME"] = home

        context.add_cleanup(restore)
        os.environ["HOME"] = str(Path(context.test_dir) / "home")

        context.add_cleanup(restore)
        tk_cli.TK_BIN = str(Path(context.project_dir) / "ticket")
        tk_cli.STATE_DIR = Path(context.test_dir) / ".state" / "tk"
        tk_cli.PROJECTS_FILE = tk_cli.STATE_DIR / "projects.json"
        # The Host allowlist accepts 127.0.0.1, not TestClient's default "testserver".
        context.api_client = TestClient(app, base_url="http://127.0.0.1")
    return context.api_client


def _send(context, method, path, body=None, headers=None):
    kwargs = {"headers": headers or {}}
    if body is not None:
        kwargs["json"] = json.loads(_expand(context, body))
    context.api_response = _client(context).request(method, _expand_path(context, path), **kwargs)


def _json(context):
    return context.api_response.json()


@given(r"the web UI was launched for the scenario directory")
def step_api_launched_for_dir(context):
    os.environ["INITIAL_PROJECT_DIR"] = context.test_dir


@given(r"the web UI was launched without the CLI")
def step_api_launched_without_cli(context):
    os.environ.pop("INITIAL_PROJECT_DIR", None)


@when(r'I send API (?P<method>GET|POST|PUT|DELETE) "(?P<path>[^"]+)"(?: with Host "(?P<host>[^"]+)")?(?: from origin "(?P<origin>[^"]+)")?')
def step_api_send(context, method, path, host=None, origin=None):
    headers = {}
    if host:
        headers["Host"] = host
    if origin:
        headers["Origin"] = origin
    _send(context, method, path, body=context.text, headers=headers)


@when(r"I remember the API tickets version")
def step_api_remember_version(context):
    _send(context, "GET", "/api/tickets/version?directory={dir}")
    context.remembered_version = _json(context)["version"]


@then(r"the API status should be (?P<status>\d+)")
def step_api_status(context, status):
    got = context.api_response.status_code
    assert got == int(status), f"Expected HTTP {status}, got {got}: {context.api_response.text}"


@then(r'the API response should be JSON')
def step_api_is_json(context):
    ctype = context.api_response.headers.get("content-type", "")
    assert ctype.startswith("application/json"), f"Expected JSON, got content-type {ctype!r}"


@then(r'the API field "(?P<field>[^"]+)" should be null')
def step_api_field_null(context, field):
    assert _json(context)[field] is None, f"Expected {field} null, got {_json(context)!r}"


@then(r'the API field "(?P<field>[^"]+)" should be the scenario directory')
def step_api_field_dir(context, field):
    assert _json(context)[field] == context.test_dir, f"Got {_json(context)!r}"


@then(r'the API field "(?P<field>[^"]+)" should match "(?P<pattern>[^"]+)"')
def step_api_field_match(context, field, pattern):
    value = _json(context)[field]
    assert isinstance(value, str) and re.fullmatch(pattern, value), f"{field}={value!r} !~ {pattern}"


@then(r'the API field "(?P<field>[^"]+)" should contain "(?P<text>[^"]+)"')
def step_api_field_contains(context, field, text):
    value = str(_json(context)[field])
    assert text in value, f"Expected {field} to contain {text!r}, got {value!r}"


@then(r"the API tickets version should have changed")
def step_api_version_changed(context):
    _send(context, "GET", "/api/tickets/version?directory={dir}")
    assert _json(context)["version"] != context.remembered_version, "Fingerprint did not change"


@then(r'the API ticket list should contain a ticket with title "(?P<title>[^"]+)"')
def step_api_list_has_title(context, title):
    _send(context, "GET", "/api/tickets?directory={dir}")
    titles = [t["title"] for t in _json(context)]
    assert title in titles, f"Title {title!r} not in {titles!r}"


@then(r'the API ticket list should contain a ticket with (?P<field>assignee|description) "(?P<value>[^"]+)"')
def step_api_list_has_field(context, field, value):
    _send(context, "GET", "/api/tickets?directory={dir}")
    values = [t.get(field) for t in _json(context)]
    assert value in values, f"{field} {value!r} not in {values!r}"


@then(r"the web UI version should match pyproject.toml and WEBUI-SPEC.md")
def step_versions_match(context):
    from tk_webui import __version__
    from tk_webui.main import app

    root = Path(context.project_dir)
    # Same lookup as .github/workflows/release.yml
    pyproject = re.search(r'^version = "([^"]+)"', (root / "pyproject.toml").read_text(), re.M).group(1)
    spec = re.search(r"\*\*Version\*\*: `([^`]+)`", (root / "tk_webui" / "WEBUI-SPEC.md").read_text()).group(1)
    found = {"__version__": __version__, "FastAPI app": app.version, "pyproject.toml": pyproject, "WEBUI-SPEC.md": spec}
    assert len(set(found.values())) == 1, f"Version drift: {found}"
