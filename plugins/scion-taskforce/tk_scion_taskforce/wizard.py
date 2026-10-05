"""Interactive `init` wizard: menu prompts with validation, plus tk/Scion project pre-flight."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from tk_scion_taskforce.config import load_yaml_file, scion_home
from tk_scion_taskforce.roles import DEFAULT_ROLES
from tk_scion_taskforce.tickets import find_tk_binary

QUIT_WORDS = ("q", "quit", "exit")
TEMPLATE_HARNESS = "gemini-cli"  # harness the seeded worker template is paired with (API-key auth)
FALLBACK_HARNESSES = ["gemini-cli", "claude", "opencode"]

# Google Cloud locations for Vertex AI. `eu`/`us` are multi-region endpoints; `global` routes anywhere.
REGION_OPTIONS = [
    ("europe-west3", "Frankfurt, EU"),
    ("global", "global endpoint; widest model availability"),
    ("eu", "EU multi-region"),
    ("europe-west4", "Netherlands, EU"),
    ("us-central1", "Iowa, US"),
    ("us-east5", "Ohio, US; Claude on Vertex AI"),
]
_REGION_RE = re.compile(r"^(global|eu|us|(africa|asia|australia|europe|me|northamerica|southamerica|us)-[a-z]+[0-9]+)$")
_PROJECT_RE = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

# shortcut: hand-maintained Vertex model IDs for opencode, whose own default picks a non-Vertex
# provider (seen: "Nano Banana Pro" + missing API key). Replace once Scion exposes per-harness model lists.
OPENCODE_VERTEX_MODELS = [
    ("google-vertex/gemini-3.5-flash", "Gemini 3.5 Flash on Vertex AI"),
    ("google-vertex/gemini-3.1-pro-preview", "Gemini 3.1 Pro on Vertex AI"),
]


class WizardAbort(Exception):
    """The user quit the wizard (q / Ctrl-C / end of input)."""


Validator = Callable[[str], Optional[str]]  # returns an error message, or None when the value is valid


def _ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt) as exc:
        print()
        raise WizardAbort from exc


def choose(
    title: str,
    options: list[tuple[str, str]],
    default: int = 0,
    validate: Validator | None = None,
    other: bool = True,
) -> str:
    """Show a numbered menu and return the chosen value.

    Enter takes the default; a number picks an option; typing a listed value also works.
    The last entry, `Other`, takes free text checked by ``validate``. Invalid input is
    re-asked; `q` quits.
    """
    print(f"\n{title}")
    for i, (value, note) in enumerate(options, 1):
        mark = "*" if i - 1 == default else " "
        label = value or "(blank)"
        print(f"  {mark}{i}) {label}" + (f"  - {note}" if note else ""))
    other_idx = len(options) + 1
    if other:
        print(f"   {other_idx}) Other (type a value)")
    values = [v for v, _ in options]
    while True:
        ans = _ask(f"Choose [{default + 1}], or q to quit: ")
        if ans.lower() in QUIT_WORDS:
            raise WizardAbort
        if not ans:
            return values[default]
        if ans.isdigit():
            n = int(ans)
            if 1 <= n <= len(options):
                return values[n - 1]
            if other and n == other_idx:
                return _ask_other(validate)
            print(f"  ✗ Pick 1-{other_idx}; choose {other_idx} to type your own value." if other else f"  ✗ Pick 1-{len(options)}.")
            continue
        if ans in values:
            return ans
        if other:
            err = validate(ans) if validate else None
            if err is None:
                return ans
            print(f"  ✗ {err}")
            continue
        print(f"  ✗ Pick 1-{len(options)}.")


def _ask_other(validate: Validator | None) -> str:
    while True:
        val = _ask("  Value (q to quit): ")
        if val.lower() in QUIT_WORDS:
            raise WizardAbort
        err = validate(val) if validate else (None if val else "Value cannot be empty.")
        if err is None:
            return val
        print(f"  ✗ {err}")


# --- validators -------------------------------------------------------------------------------


def validate_region(value: str) -> str | None:
    if _REGION_RE.match(value):
        return None
    if re.match(r"^[a-z]{2}-[a-z]+-?[0-9]$", value):
        return f"'{value}' looks like an AWS region. Google Cloud uses names like europe-west3 (Frankfurt) or global."
    return f"'{value}' is not a Google Cloud location (examples: europe-west3, us-central1, global, eu)."


def validate_gcp_project(value: str) -> str | None:
    if _PROJECT_RE.match(value):
        return None
    return "Project IDs are 6-30 chars: lowercase letters, digits, hyphens; start with a letter."


def validate_tag(value: str) -> str | None:
    return None if _TAG_RE.match(value) else "Tags use letters, digits, '-', '_' or '.', with no spaces or commas."


def validate_model(value: str) -> str | None:
    if not value:
        return "Model cannot be empty; pick the harness default option instead."
    if len(value) > 100 or any(c in value for c in "\"\\\n"):
        return "Model IDs cannot contain quotes, backslashes or newlines."
    return None


def validate_workers(value: str) -> str | None:
    return None if value.isdigit() and 1 <= int(value) <= 10 else "Enter a whole number from 1 to 10."


def validate_roles(value: str) -> str | None:
    names = [n.strip() for n in value.split(",")]
    if all(_TAG_RE.match(n) for n in names):
        return None
    return "List role names separated by commas, e.g. developer,code-reviewer."


def harness_validator(installed: list[str]) -> Validator:
    def _check(value: str) -> str | None:
        if not _TAG_RE.match(value):
            return "Harness names use letters, digits, '-', '_' or '.'."
        if installed and value not in installed:
            return f"'{value}' is not installed (installed: {', '.join(installed)}); see `scion harness-config list`."
        return None

    return _check


# --- the wizard -----------------------------------------------------------------------------


def run_wizard(defaults: dict, installed: list[str]) -> dict:
    """Ask the setup questions as validated menus. Raises WizardAbort when the user quits."""
    print("=" * 60)
    print("🚀 SCION Task Force Setup Wizard")
    print("=" * 60)
    print("Pick a number, press Enter for the default (*), choose Other to type a value, or q to quit.")

    harnesses = installed or FALLBACK_HARNESSES
    h_default = harnesses.index(defaults["harness"]) if defaults["harness"] in harnesses else 0
    harness = choose(
        "1. Scion harness (the agent CLI inside each worker)",
        [(h, "recommended: API-key auth, matches the worker template" if h == TEMPLATE_HARNESS else "") for h in harnesses],
        default=h_default,
        validate=harness_validator(installed),
    )
    m_opts = model_options(harness)
    m_values = [v for v, _ in m_opts]
    m_default = 0 if harness == "opencode" or "medium" not in m_values else m_values.index("medium")
    model = choose("2. Model", m_opts, default=m_default, validate=validate_model)

    gcp_project = gcp_region = ""
    if harness == TEMPLATE_HARNESS:
        print("\n3-4. Google Cloud: skipped; gemini-cli authenticates with the GEMINI_API_KEY Scion secret.")
    else:
        proj = defaults["gcp_project"]
        if proj:
            gcp_project = choose(
                "3. Google Cloud project (Vertex AI)", [(proj, "detected from gcloud/env")], validate=validate_gcp_project
            )
        else:
            print("\n3. Google Cloud project (Vertex AI): none detected.")
            gcp_project = _ask_other(validate_gcp_project)
        gcp_region = choose("4. Google Cloud location (Vertex AI)", REGION_OPTIONS, validate=validate_region)
    claim_tag = choose("5. Opt-in tag (tickets you tag with it go to the task force)", [("taskforce", "")], validate=validate_tag)
    max_concurrent = int(
        choose(
            "6. Max concurrent workers in this project",
            [("1", "recommended: workers share one checkout"), ("2", ""), ("3", "")],
            validate=validate_workers,
        )
    )

    privacy = choose(
        "7. Privacy (what workers may share outside this machine)",
        [
            ("confidential", "recommended: no uploads, public links, pushes or PR comments"),
            ("standard", "no extra restrictions"),
        ],
        other=False,
    )
    roles = choose(
        "8. agent-team skills in .agents/skills/tk-scion-* (github.com/scion-frontiers/agent-team; tag a ticket role:<name>)",
        [("recommended", ", ".join(DEFAULT_ROLES)), ("none", "no role skills; the worker uses only its brief")],
        validate=validate_roles,
    )

    answers = {
        "harness": harness,
        "model": model,
        "gcp_project": gcp_project,
        "gcp_region": gcp_region,
        "claim_tag": claim_tag,
        "max_concurrent": max_concurrent,
        "privacy": privacy,
        "roles": roles,
    }
    print("\nSummary:")
    for key, val in answers.items():
        print(f"  {key:<15} {val if val != '' else '(harness default)'}")
    ans = _ask("Write this configuration? [Y/n]: ").lower()
    if ans not in ("", "y", "yes"):
        raise WizardAbort
    return answers


# --- Scion discovery --------------------------------------------------------------------------


def _read_yaml(path: Path) -> dict:
    """Read a Scion YAML file; {} when missing or unparsable (it is outside our control)."""
    try:
        return load_yaml_file(path)
    except Exception:  # noqa: BLE001 - discovery is best effort
        return {}


def installed_harnesses(binary: str = "scion") -> list[str]:
    """Harness-config names from `scion harness-config list`; empty when Scion is unavailable."""
    if not shutil.which(binary):
        return []
    try:
        proc = subprocess.run(
            [binary, "--non-interactive", "harness-config", "list"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    names: list[str] = []
    in_table = False
    for line in proc.stdout.splitlines():
        cols = line.split()
        if cols[:1] == ["NAME"]:
            in_table = True
            continue
        if in_table and cols:
            names.append(cols[0])
    return names


def default_harness(installed: list[str]) -> str:
    """`gemini-cli` (the standard worker template's pairing) when installed or unknown;
    else Scion's own default harness, else the first installed."""
    if not installed or TEMPLATE_HARNESS in installed:
        return TEMPLATE_HARNESS
    settings = scion_home() / "settings.yaml"
    preferred = str(_read_yaml(settings).get("default_harness_config", "") or "")
    return preferred if preferred in installed else installed[0]


def model_options(harness: str) -> list[tuple[str, str]]:
    """Model menu for ``harness``: Vertex IDs (opencode), the harness's size aliases, then its default."""
    opts: list[tuple[str, str]] = list(OPENCODE_VERTEX_MODELS) if harness == "opencode" else []
    cfg_file = scion_home() / "harness-configs" / harness / "config.yaml"
    aliases = _read_yaml(cfg_file).get("model_aliases", {})
    for alias in ("small", "medium", "large", "extra-large"):
        if isinstance(aliases, dict) and aliases.get(alias):
            opts.append((alias, f"Scion alias -> {aliases[alias]}"))
    opts.append(("", f"let {harness} pick its own default model"))
    return opts


def resolve_model_alias(harness: str, model: str) -> str:
    """Concrete model ID for a Scion size alias (``medium`` -> ``gemini-3.5-flash``); else ``model``.

    Scion resolves aliases on `start` but stores the alias and passes it verbatim on `resume`
    (`gemini --resume --model medium`), which the harness rejects. Starting with the concrete ID
    keeps resumed workers (follow-up notes, review feedback) on a valid model.
    """
    if not model:
        return model
    if not harness:
        settings = _read_yaml(scion_home() / "settings.yaml")
        harness = str(settings.get("default_harness_config", "") or TEMPLATE_HARNESS)
    aliases = _read_yaml(scion_home() / "harness-configs" / harness / "config.yaml").get("model_aliases", {})
    resolved = aliases.get(model) if isinstance(aliases, dict) else None
    return str(resolved) if resolved else model


# --- pre-flight: tk init / scion init ---------------------------------------------------------


def ensure_project_initialized(project_dir: Path, scion_binary: str = "scion") -> None:
    """Run `tk init` and `scion init` in ``project_dir`` when they have not been run yet.

    Best effort: failures are reported, never raised, so `init` can still write its config.
    """
    if (project_dir / ".tickets").is_dir():
        print("✓ tk: .tickets/ already initialized")
    else:
        tk_bin = find_tk_binary(project_dir)
        if not tk_bin:
            print("⚠️  tk: not found on PATH; run `tk init` yourself.")
        else:
            res = subprocess.run([tk_bin, "super", "init", str(project_dir)], capture_output=True, text=True)
            print(f"{'✓' if res.returncode == 0 else '⚠️ '} tk init: {(res.stdout or res.stderr).strip()}")

    if (project_dir / ".scion").exists():
        print("✓ scion: .scion already initialized")
    elif not shutil.which(scion_binary):
        print(f"⚠️  scion: `{scion_binary}` not found on PATH; install Scion, then run `scion init`.")
        return
    else:
        try:
            res = subprocess.run(
                [scion_binary, "--non-interactive", "init"],
                cwd=str(project_dir),
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            print(f"⚠️  scion init failed: {exc}")
            return
        if res.returncode != 0:
            print(f"⚠️  scion init failed: {(res.stderr or res.stdout).strip()[:300]}")
        elif (project_dir / ".scion").exists():
            print("✓ scion init: created .scion")
        else:
            print(f"⚠️  scion init ran, but {project_dir}/.scion/ is missing (Scion initializes the git root).")
    fixed = ensure_scion_agents_ignored(project_dir)
    if fixed:
        print(f"✓ {fixed}")


def ensure_scion_agents_ignored(project_dir: Path) -> str:
    """Make git ignore `.scion/agents/` (agent homes, staged secrets) when ``project_dir`` is in a git repo.

    Scion refuses to start workers in a git repo unless that path is ignored (`CheckAgentsGitignore`,
    which uses `git check-ignore`). The entry goes to the repo's local `.git/info/exclude`: untracked,
    never pushed, and the user's `.gitignore` stays untouched. Plain folders need nothing.
    Returns a one-line description of the change, or ``""`` when nothing was needed.
    """
    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(["git", "-C", str(project_dir), *args], capture_output=True, text=True)

    if not shutil.which("git"):
        return ""
    top = git("rev-parse", "--show-toplevel")
    if top.returncode != 0:
        return ""  # not a git repo: Scion does not check
    if git("check-ignore", "-q", ".scion/agents/").returncode == 0:
        return ""
    try:
        rel = (project_dir.resolve() / ".scion" / "agents").relative_to(Path(top.stdout.strip()).resolve())
    except ValueError:
        return ""
    exclude = Path(git("rev-parse", "--git-path", "info/exclude").stdout.strip())
    if not exclude.is_absolute():
        exclude = project_dir / exclude
    entry = f"/{rel.as_posix()}/"
    text = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text(text + ("" if not text or text.endswith("\n") else "\n") + entry + "\n", encoding="utf-8")
    return f"auto-fix: added `{entry}` to {exclude} (Scion requires it in git repos; local file, never committed)"
