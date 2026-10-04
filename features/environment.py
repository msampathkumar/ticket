"""Behave environment setup for ticket CLI tests."""

import os
import shutil
import tempfile
from pathlib import Path


def before_all(context):
    """Set up test environment before all tests."""
    # Store the project directory (where the ticket script lives)
    context.project_dir = Path(__file__).parent.parent.resolve()

    # Add project plugins to PATH so extracted commands are found
    plugins_dir = context.project_dir / 'plugins'
    if plugins_dir.exists():
        os.environ['PATH'] = str(plugins_dir) + ':' + os.environ.get('PATH', '')

    # Never let the suite reach the developer's real `scion`/Hub: a real `scion hub link` on a
    # temp dir creates a stray Hub project (`ticket-test-xxxxxxxx`). Scenarios that need a runtime
    # install the fake `scion` in context.plugin_dir, which is prepended later and wins.
    context.scion_guard_dir = tempfile.mkdtemp(prefix='tk_scion_guard_')
    guard = Path(context.scion_guard_dir) / 'scion'
    guard.write_text('#!/bin/sh\necho "real scion is blocked in tests" >&2\nexit 97\n')
    guard.chmod(0o755)
    os.environ['PATH'] = context.scion_guard_dir + ':' + os.environ['PATH']


def after_all(context):
    """Remove the scion guard directory."""
    if getattr(context, 'scion_guard_dir', None) and os.path.exists(context.scion_guard_dir):
        shutil.rmtree(context.scion_guard_dir)


def before_scenario(context, scenario):
    """Create a fresh temporary directory for each scenario."""
    # Create a temporary directory for this scenario
    context.test_dir = tempfile.mkdtemp(prefix='ticket_test_')
    os.environ['TK_SCION_TASKFORCE_STATE_DIR'] = str(Path(context.test_dir) / '.state')
    os.environ['TK_SCION_TASKFORCE_LOG_DIR'] = str(Path(context.test_dir) / '.state' / 'logs')
    # Isolate from the developer's real ~/.config/tk/scion-taskforce.yaml
    os.environ['XDG_CONFIG_HOME'] = str(Path(context.test_dir) / '.config')
    # ...and from the developer's real ~/.scion (default harness, harness model aliases)
    os.environ['TK_SCION_TASKFORCE_SCION_HOME'] = str(Path(context.test_dir) / '.scion-home')

    # Initialize tracking
    context.tickets = {}
    context.last_created_id = None
    context.stdout = ''
    context.stderr = ''
    context.returncode = None


def after_scenario(context, scenario):
    """Clean up temporary directories after each scenario."""
    if hasattr(context, 'test_dir') and os.path.exists(context.test_dir):
        shutil.rmtree(context.test_dir)
    if hasattr(context, 'plugin_dir') and os.path.exists(context.plugin_dir):
        shutil.rmtree(context.plugin_dir)
    for var in ('FAKE_SCION_STATE', 'FAKE_SCION_MODE', 'FAKE_SCION_HUB', 'FAKE_SCION_WORKER_REPORT', 'FAKE_SCION_FAIL_CMDS',
                'FAKE_SCION_ACTIVITY',
                'XDG_CONFIG_HOME', 'TK_SCION_TASKFORCE_SCION_HOME', 'TK_HOOKS_SYNC', 'TK_HOOK_DEPTH', 'TK_NO_HOOKS'):
        os.environ.pop(var, None)


def before_feature(context, feature):
    """Called before each feature file is processed."""
    pass


def after_feature(context, feature):
    """Called after each feature file is processed."""
    pass
