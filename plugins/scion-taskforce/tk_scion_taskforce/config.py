"""Configuration loader and starter template generator for tk-scion-taskforce."""

from __future__ import annotations

import copy
import os
import re
import shutil
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None

# Seeded per project by `init`; modelled on a known-good Scion agent (gemini-cli + API-key auth).
WORKER_TEMPLATE = "tk-worker-gemini-cli-with-api-key-auth"
# deprecated: template name used before 2026-10, only removed by `uninit`; remove after 2027-01-01
LEGACY_TEMPLATES = ("taskforce-worker",)


class ConfigError(ValueError):
    """A config file cannot be read reliably."""


# shortcut: the `watcher:` section is named after the removed polling daemon; rename it (reading the
# old name as a fallback) when the config schema next changes.
DEFAULT_CONFIG: dict[str, Any] = {
    "tags": {
        "claim": "taskforce",
        "ignore": "no-taskforce",
        "review": "waiting-for-review",
    },
    "watcher": {
        "max_concurrent": 10,
        "max_concurrent_per_project": 1,
        "spawn_verify_timeout_seconds": 30,
        "spawn_verify_poll_seconds": 2,
        "gc_retention_days": 5,
    },
    "worker": {
        "git": "off",
        "privacy": "confidential",
        "prompt_file": "",
        "review_tags": ["pr", "review"],
        "review_ref_prefixes": ["gh-pr-"],
    },
    "provider": {
        "binary": "scion",
        "profile": "",
        "template": WORKER_TEMPLATE,
        "harness_config": "",
        "model": "",
        "gcp_project": "",
        "gcp_region": "",
        "branch_prefix": "",
        "extra_start_args": [],
        "extra_resume_args": [],
    },
    "telemetry": {
        "enabled": True,
        "log_dir": "~/.local/state/tk/scion-taskforce/logs",
        "project_log_symlink": True,
        "rotation": {
            "enabled": True,
            "max_bytes": 104857600,
            "retention_days": 30,
            "compress": True,
        },
    },
}

STARTER_YAML_TEMPLATE = """# scion-taskforce.yaml — Configuration for tk-scion-taskforce (the full key reference)
# Precedence, low to high (later files are deep-merged over earlier ones):
#   built-in defaults
#   < ~/.config/tk/scion-taskforce.yaml                 (global; `init --global`; honours $XDG_CONFIG_HOME)
#   < <project>/.scion-taskforce/scion-taskforce.yaml   (project; `init`)
#   < $TK_SCION_TASKFORCE_CONFIG                        (file path)
#   < --config <path>

# 1. Ticket Tags (customizable)
#    The task force is OPT-IN: it only picks up ready (unblocked, open) tickets that
#    *you* tagged with `tags.claim`. It never adds that tag on its own.
tags:
  claim: taskforce                # Opt-in tag the USER adds to hand a ticket to the task force
  ignore: no-taskforce            # Tickets with this tag are never picked up (safety override)
  review: waiting-for-review      # Added by the worker when it finishes and pauses for review

# 2. Concurrency & Launch Settings (section name kept from the removed daemon)
watcher:
  max_concurrent: 10              # Maximum total running workers across all projects
  max_concurrent_per_project: 1   # Max running workers per project; the next queued ticket starts when one
                                  # pauses or closes. SAFETY: each worker mounts the project checkout
                                  # (`scion start -w <project>`), so workers in ONE project share a working
                                  # tree and can fight over branches. Raise above 1 only if you accept that.
  spawn_verify_timeout_seconds: 30 # Wait up to N s for a spawned pod to report 'running' before claiming
  spawn_verify_poll_seconds: 2    # Poll interval while verifying a freshly spawned pod
  gc_retention_days: 5            # Days after a ticket closes before `gc` deletes its stopped worker

# 3. Worker Prompt Settings
#    Workers get an auto-generated brief: "implement" for normal tickets, "review" for
#    pull-request tickets (e.g. synced by `tk github sync --prs`). Both explain how to
#    report back even when `tk` is not installed inside the pod.
worker:
  git: "off"                      # off: workers never change git state (no init/commit/checkout/push); they
                                  #   leave changes in the working tree and list them. Works in plain folders.
                                  # branch: workers commit on the ticket branch (never push). Git repos only.
  privacy: "confidential"         # confidential: the brief forbids uploads, public links, pushes and PR
                                  #   comments; `templates install` drops publishing skills.
                                  # standard: no extra restrictions.
  prompt_file: ""                 # Optional path to a custom prompt template. Placeholders:
                                  # {ticket_id} {project_dir} {branch} {ticket_details} {work_type}
                                  # {claim_tag} {review_tag} {external_ref} {ticket_title}
  review_tags: [pr, review]       # A ticket with any of these tags gets the REVIEW brief
  review_ref_prefixes: [gh-pr-]   # ...or whose external-ref starts with one of these prefixes

# 4. Scion Worker Settings
provider:
  binary: scion                   # Path or command name for the provider CLI
  profile: ""                     # Optional SCION runtime profile (--profile)
  template: "tk-worker-gemini-cli-with-api-key-auth"  # Project-level SCION template (.scion/templates/<name>)
  harness_config: "gemini-cli"    # Scion harness-config (see `scion harness-config list`)
  model: ""                       # Model ID or Scion alias (small|medium|large); aliases are resolved to a
                                  # model ID at start so resumed workers keep a valid model; blank = harness default
  gcp_project: ""                 # Vertex AI project (GOOGLE_CLOUD_PROJECT); blank = inherit from env
  gcp_region: ""                  # Vertex AI location, e.g. europe-west3 or global; blank = env or fallback
  branch_prefix: ""               # Branch prefix for worker.git: branch (default branch: <ticket-id>)
  extra_start_args: ["--harness-auth", "api-key"] # gemini-cli: GEMINI_API_KEY (Scion secret); other harnesses: vertex-ai
  extra_resume_args: []           # Additional flags passed to 'scion resume'

# 5. OpenTelemetry & Local Log Rotation Settings
telemetry:
  enabled: true                   # Write spans and metrics; taskforce.log and worker logs are always written
  log_dir: ~/.local/state/tk/scion-taskforce/logs
  project_log_symlink: true       # Symlink <project>/.tickets/.scion-taskforce-logs -> global log dir
                                  # Files: otel-traces.jsonl, otel-metrics.jsonl, taskforce.log, workers/
  rotation:
    enabled: true                 # Rotate logs daily at UTC midnight
    max_bytes: 104857600          # Also rotate if active log exceeds 100 MB
    retention_days: 30            # `gc` deletes rotated logs older than N days
    compress: true                # Gzip rotated log files (.gz)
"""


def global_config_path() -> Path:
    """``$XDG_CONFIG_HOME/tk/scion-taskforce.yaml`` (default ``~/.config/tk/scion-taskforce.yaml``)."""
    base = os.environ.get("XDG_CONFIG_HOME", "").strip()
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "tk" / "scion-taskforce.yaml"


def project_config_path(project_dir: Path | str) -> Path:
    """``<project>/.scion-taskforce/scion-taskforce.yaml``, written by `init`."""
    return Path(project_dir).expanduser().resolve() / ".scion-taskforce" / "scion-taskforce.yaml"


def _parse_scalar(val: str) -> Any:
    val = val.strip()
    if val in ("[]", "[ ]"):
        return []
    if val in ("{}", "{ }"):
        return {}
    if val.lower() == "true":
        return True
    if val.lower() == "false":
        return False
    if val.lower() in ("null", "none", "~"):
        return None
    if (val.startswith('"') and val.endswith('"')) or (
        val.startswith("'") and val.endswith("'")
    ):
        return val[1:-1]
    if val.startswith("[") and val.endswith("]"):
        inner = val[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part) for part in inner.split(",")]
    try:
        return int(val)
    except ValueError:
        pass
    try:
        return float(val)
    except ValueError:
        pass
    return val


def _fallback_parse_yaml(text: str, source: str = "config") -> dict[str, Any]:
    """Parser for the subset of YAML that `init` writes: nested ``key: value`` mappings and inline
    ``[a, b]`` lists. Raises ``ConfigError`` on anything else instead of mis-reading it."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]

    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line_no_comment = raw_line
        in_single = False
        in_double = False
        for idx, ch in enumerate(raw_line):
            if ch == "'" and not in_double:
                in_single = not in_single
            elif ch == '"' and not in_single:
                in_double = not in_double
            elif (
                ch == "#"
                and not in_single
                and not in_double
                and (idx == 0 or raw_line[idx - 1].isspace())
            ):
                line_no_comment = raw_line[:idx]
                break

        stripped = line_no_comment.strip()
        if not stripped or stripped == "---":
            continue
        key, colon, rest = stripped.partition(":")
        rest = rest.strip()
        unsupported = (
            "a block list item ('- ...')" if stripped.startswith("-")
            else "a line without 'key: value'" if not colon
            else "a multi-line string" if rest[:1] in ("|", ">")
            else "an inline mapping" if rest.startswith("{") and rest.replace(" ", "") != "{}"
            else "an anchor or alias" if rest[:1] in ("&", "*")
            else ""
        )
        if unsupported:
            raise ConfigError(
                f"{source}:{line_no}: {unsupported} needs PyYAML. Install it (`pip install pyyaml`) or "
                "run `tk scion-taskforce` from the repo's .venv, or rewrite the value inline."
            )

        indent = len(line_no_comment) - len(line_no_comment.lstrip(" "))
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        current_dict = stack[-1][1]
        key = key.strip()
        if not rest:
            new_section: dict[str, Any] = {}
            current_dict[key] = new_section
            stack.append((indent, new_section))
        else:
            current_dict[key] = _parse_scalar(rest)

    return root


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _deep_merge(merged[k], v)
        else:
            merged[k] = v
    return merged


def load_yaml_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    text = path.read_text(encoding="utf-8")
    if yaml is not None:
        loaded = yaml.safe_load(text)
        return loaded if isinstance(loaded, dict) else {}
    return _fallback_parse_yaml(text, source=str(path))


def resolve_config_path(
    project_dir: Path | None = None,
    explicit_config: str | None = None,
) -> Path | None:
    if explicit_config:
        candidate = Path(explicit_config).expanduser().resolve()
        if candidate.exists():
            return candidate
    env_cfg = os.environ.get("TK_SCION_TASKFORCE_CONFIG")
    if env_cfg:
        candidate = Path(env_cfg).expanduser().resolve()
        if candidate.exists():
            return candidate
    if project_dir is not None:
        p = Path(project_dir).expanduser().resolve()
        proj_cfg = project_config_path(p)
        if proj_cfg.exists():
            return proj_cfg
    global_cfg = global_config_path()
    if global_cfg.exists():
        return global_cfg
    return None


def load_config(
    project_dir: Path | None = None,
    explicit_config: str | None = None,
) -> dict[str, Any]:
    """Load merged configuration following precedence rules."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)

    global_cfg = global_config_path()
    if global_cfg.exists():
        cfg = _deep_merge(cfg, load_yaml_file(global_cfg))

    if project_dir is not None:
        proj_cfg = project_config_path(project_dir)
        if proj_cfg.exists():
            cfg = _deep_merge(cfg, load_yaml_file(proj_cfg))

    env_cfg = os.environ.get("TK_SCION_TASKFORCE_CONFIG")
    if env_cfg:
        env_path = Path(env_cfg).expanduser().resolve()
        if env_path.exists():
            cfg = _deep_merge(cfg, load_yaml_file(env_path))

    if explicit_config:
        exp_path = Path(explicit_config).expanduser().resolve()
        if exp_path.exists():
            cfg = _deep_merge(cfg, load_yaml_file(exp_path))

    return cfg


WORKER_TEMPLATE_FILES = {
    "scion-agent.yaml": f"""# {WORKER_TEMPLATE}: standard tk task force worker.
# Pairs with harness `gemini-cli` + `--harness-auth api-key` (set in scion-taskforce.yaml), the setup
# proven by a hand-made Scion agent. Per Scion's template rules, harness/harness_config are NOT set here.
schema_version: "1"
description: "tk task force worker: works on one tk ticket, then reports back in the ticket for review"
agent_instructions: agents.md
system_prompt: system-prompt.md
""",
    "agents.md": """# tk Task Force Worker

You own exactly one `tk` ticket. Its ID and full details are in your task prompt.

## Work
1. Read the ticket and its acceptance criteria before changing anything.
2. Make the smallest change that meets them. Follow the repository's AGENTS.md / CONTRIBUTING.md.
3. Run the project's tests and linters; fix what you broke.

## Report back
- Record what you changed, how you verified it and any open questions as a note in
  `.tickets/<id>.md` (use `tk add-note <id> "..."` when `tk` is installed).
- Add the review tag named in your task prompt (default `waiting-for-review`), then stop. Review feedback arrives as a new note.

## Git and confidentiality
- Follow the git and confidentiality rules in your task prompt. Git is optional: never run `git init`.
- Never push. The checkout may be shared with a human.
""",
    "system-prompt.md": """# Software Engineer (tk Task Force)

You are a careful senior engineer working autonomously on one ticket. You prefer small, verified
changes over broad rewrites, state assumptions explicitly, and report honestly what you did not finish.
""",
}


def seed_project_scion_template(project_dir: Path, force: bool = False) -> Path:
    """Seed <project>/.scion/templates/<WORKER_TEMPLATE>/. Existing files are kept unless ``force``,
    except that the pre-2026-10 git section of agents.md is replaced in place (other edits are kept)."""
    tmpl_dir = project_dir / ".scion" / "templates" / WORKER_TEMPLATE
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    for name, content in WORKER_TEMPLATE_FILES.items():
        target = tmpl_dir / name
        if force or not target.exists():
            target.write_text(content, encoding="utf-8")
    agents = tmpl_dir / "agents.md"
    text = agents.read_text(encoding="utf-8")
    if _OLD_GIT_SECTION in text:
        text = text.replace(_OLD_GIT_SECTION + _OLD_GIT_EXTRA, _OLD_GIT_SECTION).replace(_OLD_GIT_SECTION, _NEW_GIT_SECTION)
        agents.write_text(text, encoding="utf-8")
    return tmpl_dir


# deprecated: git section seeded before worker.git existed (it told workers to commit); remove after 2027-01-01
_OLD_GIT_SECTION = """## Git
- Commit on your ticket branch only. Do not push, merge, rebase onto other branches or `git stash`;
  the checkout may be shared with a human.
"""
_OLD_GIT_EXTRA = "- If the workspace is not a git repository, never run `git init`: skip committing and say so in your report.\n"
_NEW_GIT_SECTION = "## Git and confidentiality" + WORKER_TEMPLATE_FILES["agents.md"].split("## Git and confidentiality", 1)[1]


def set_yaml_value(text: str, section: str, key: str, value: str) -> str:
    """Set top-level ``section``'s ``key`` to the YAML literal ``value``, keeping comments and layout.
    Adds the key (and section) when missing."""
    lines = text.splitlines(keepends=True)
    header = None
    for i, line in enumerate(lines):
        if line[:1] not in ("", " ", "#", "\n") and line.split(":", 1)[0].strip() == section:
            header = i
            continue
        if header is None:
            continue
        if line[:1] not in (" ", "#", "\n"):
            break  # next top-level key: the section has no such key
        m = re.match(rf"^(\s+{re.escape(key)}:\s*)(.*?)(\s+#.*)?$", line.rstrip("\n"))
        if m:
            lines[i] = f"{m.group(1)}{value}{m.group(3) or ''}\n"
            return "".join(lines)
    if header is None:
        return text + ("" if text.endswith("\n") else "\n") + f"\n{section}:\n  {key}: {value}\n"
    lines.insert(header + 1, f"  {key}: {value}\n")
    return "".join(lines)


def _answer_values(answers: dict[str, Any]) -> dict[tuple[str, str], str]:
    """Config keys set by the `init` wizard, as YAML literals."""
    auth = "api-key" if answers["harness"] == "gemini-cli" else "vertex-ai"
    return {
        ("tags", "claim"): str(answers["claim_tag"]),
        ("worker", "privacy"): f'"{answers.get("privacy", "confidential")}"',
        ("watcher", "max_concurrent_per_project"): str(answers["max_concurrent"]),
        ("provider", "harness_config"): f'"{answers["harness"]}"',
        ("provider", "model"): f'"{answers["model"]}"',
        ("provider", "gcp_project"): f'"{answers["gcp_project"]}"',
        ("provider", "gcp_region"): f'"{answers["gcp_region"]}"',
        ("provider", "extra_start_args"): f'["--harness-auth", "{auth}"]',
    }


def init_config(
    project_dir: Path | None = None,
    global_scope: bool = False,
    force: bool = False,
    answers: dict[str, Any] | None = None,
) -> tuple[Path, str]:
    """Write the global or project config and, for a project, seed the worker template.

    A new file starts from ``STARTER_YAML_TEMPLATE``; an existing one keeps the user's values
    (``force`` starts over). ``answers`` (wizard keys) are written into either.
    Returns ``(path, "created" | "updated" | "kept")``.
    """
    base_dir = Path(project_dir or Path.cwd()).expanduser().resolve()
    target = global_config_path() if global_scope else project_config_path(base_dir)
    existed = target.exists() and not force
    text = target.read_text(encoding="utf-8") if existed else STARTER_YAML_TEMPLATE
    for (section, key), value in (_answer_values(answers) if answers else {}).items():
        text = set_yaml_value(text, section, key, value)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    if not global_scope:
        seed_project_scion_template(base_dir, force=force)
    if not existed:
        return target, "created"
    return target, "updated" if answers else "kept"


def uninit_config(
    project_dir: Path | None = None,
    global_scope: bool = False,
) -> tuple[bool, str]:
    """Remove .scion-taskforce/ directory or global config file."""
    if global_scope:
        target = global_config_path()
        if target.exists():
            target.unlink()
            return True, str(target)
        return False, str(target)

    base_dir = Path(project_dir or Path.cwd()).expanduser().resolve()
    scion_dir = base_dir / ".scion-taskforce"
    removed_any = False
    if scion_dir.is_dir():
        shutil.rmtree(scion_dir)
        removed_any = True
    tmpl_root = base_dir / ".scion" / "templates"
    # Generated role templates carry an UPSTREAM.md marker; hand-made templates are left alone.
    role_dirs = [m.parent for m in tmpl_root.glob("tk-*/UPSTREAM.md")]
    for tmpl_dir in [tmpl_root / n for n in (WORKER_TEMPLATE, *LEGACY_TEMPLATES)] + role_dirs:
        if tmpl_dir.is_dir():
            shutil.rmtree(tmpl_dir)
            removed_any = True
    return removed_any, str(scion_dir)

