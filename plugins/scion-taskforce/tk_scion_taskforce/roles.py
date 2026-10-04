"""Role templates from scion-frontiers/agent-team, installed per project with the tk contract on top.

`templates install` downloads upstream once at a pinned commit, vendors every referenced skill into the
template's ``skills/`` directory (so nothing is fetched when a worker starts) and records the sources in
``UPSTREAM.md``. A ticket tagged ``role:<name>`` then runs on ``.scion/templates/tk-<name>/``.
"""

from __future__ import annotations

import io
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

UPSTREAM_REPO = "scion-frontiers/agent-team"
UPSTREAM_REF = "3650f1b03411116fcbf37852bfec6911db64b569"  # pinned; `templates install --ref <sha>` overrides
ROLE_TAG = "role:"
TEMPLATE_PREFIX = "tk-"
MARKER = "UPSTREAM.md"  # marks a generated role template (uninit and --force only touch these)
# Installed when `templates install` gets no role names. Left out: coordinator and eng-manager
# (tk is the coordinator), release-notes (scheduled flow), qa-tester and web-builder (on request).
DEFAULT_ROLES = (
    "developer",
    "code-reviewer",
    "investigator",
    "doc-writer",
    "test-engineer",
    "security-auditor",
    "researcher",
    "architect",
)
# Skills that publish project content outside the machine; dropped when worker.privacy is confidential.
PUBLISHING_SKILLS = {"gcs-artifact-publishing": "publishes public links to a shared bucket"}

TK_CONTRACT = """# tk Task Force Worker: {role}

You own exactly one `tk` ticket. Your task prompt holds its ID, its details and the rules for git and
confidentiality in this project.

## tk contract (wins over the role guidance below)
- Work alone. There is no coordinator, manager or other agent to message; the ticket is your only channel.
- Use `tk` for updates (normally on your PATH; check `command -v tk`). Read the ticket and new feedback
  with `tk show <id>`, again whenever you resume. Share progress and questions with `tk add-note <id> "..."`.
- Report with `tk add-note`: what you did, how you verified it and any open questions. Then add the review
  tag named in your task prompt (default `waiting-for-review`) with `tk update <id> --tags ...`, keeping the
  existing tags, and stop. Change only your own ticket; never close, reopen or create tickets.
- Follow the git rule in your task prompt. Never run `git init`. Never push unless the ticket asks for it.
- Where the role guidance says to message a coordinator, push to signal completion, or write to
  `.design/` or a project log, put that content in your ticket report instead.
- Do not publish or upload project content unless the ticket asks for it.

## Role guidance (upstream `agent-team/templates/{role}`)

"""


class RoleInstallError(Exception):
    """Role templates could not be installed; nothing was changed for the failing role."""


@dataclass
class InstallResult:
    role: str
    template_dir: Path
    action: str  # "installed" | "updated" | "kept"
    skills: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)


def template_name(role: str) -> str:
    return f"{TEMPLATE_PREFIX}{role}"


def ticket_role(tags: Iterable[str]) -> str:
    """The role named by a ``role:<name>`` tag, or ``""``."""
    for tag in tags:
        if str(tag).startswith(ROLE_TAG) and len(str(tag)) > len(ROLE_TAG):
            return str(tag)[len(ROLE_TAG):].strip()
    return ""


def role_template_for(project_dir: Path, tags: Iterable[str]) -> tuple[str, str]:
    """``(role, template)`` for a ticket. ``template`` is ``""`` when there is no role tag or its
    template is not installed in the project."""
    role = ticket_role(tags)
    if not role:
        return "", ""
    name = template_name(role)
    return role, name if (project_dir / ".scion" / "templates" / name).is_dir() else ""


def installed_roles(project_dir: Path) -> list[tuple[str, str]]:
    """``(role, source line)`` for every generated role template in the project."""
    root = project_dir / ".scion" / "templates"
    found = []
    for marker in sorted(root.glob(f"{TEMPLATE_PREFIX}*/{MARKER}")):
        source = next((ln for ln in marker.read_text(encoding="utf-8").splitlines() if ln.startswith("| Source")), "")
        found.append((marker.parent.name[len(TEMPLATE_PREFIX):], source.split("|")[2].strip() if source else ""))
    return found


def generated_template_dirs(project_dir: Path) -> list[Path]:
    root = project_dir / ".scion" / "templates"
    return [m.parent for m in sorted(root.glob(f"{TEMPLATE_PREFIX}*/{MARKER}"))]


# --- fetching -----------------------------------------------------------------------------------


class _Sources:
    """Repository trees, from a local mirror (``--from <dir>`` holding ``<owner>/<repo>/``) or from
    GitHub tarballs. Each repo is fetched once; ``refs`` records the commit actually used."""

    def __init__(self, workdir: Path, mirror: Path | None) -> None:
        self.workdir = workdir
        self.mirror = mirror
        self.trees: dict[str, Path] = {}
        self.refs: dict[str, str] = {}

    def tree(self, repo: str, ref: str) -> Path:
        key = f"{repo}@{ref}"
        if key in self.trees:
            return self.trees[key]
        if self.mirror is not None:
            root = self.mirror / repo
            if not root.is_dir():
                raise RoleInstallError(f"{repo} not found in {self.mirror} (expected {root})")
            self.refs[key] = f"local copy {root}"
        else:
            root, sha = self._download(repo, ref)
            self.refs[key] = sha
        self.trees[key] = root
        return root

    def _download(self, repo: str, ref: str) -> tuple[Path, str]:
        data = _http_get(f"https://api.github.com/repos/{repo}/tarball/{ref}", f"{repo}@{ref}")
        dest = Path(tempfile.mkdtemp(prefix="repo-", dir=self.workdir))
        _safe_extract(data, dest)
        tops = [p for p in dest.iterdir() if p.is_dir()]
        if len(tops) != 1:
            raise RoleInstallError(f"unexpected archive layout for {repo}@{ref}")
        # GitHub names the top directory <owner>-<repo>-<short sha>.
        return tops[0], tops[0].name.rsplit("-", 1)[-1]


def _http_get(url: str, label: str) -> bytes:
    """GET ``url``. Prefers `curl`, which uses the system certificate store (python.org builds of
    Python often have none); falls back to urllib. ``GITHUB_TOKEN`` raises GitHub's rate limit and is
    passed via curl's stdin config, never on the command line."""
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    headers = {"User-Agent": "tk-scion-taskforce", "Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    curl = shutil.which("curl")
    if curl:
        config = "".join(f'header = "{k}: {v}"\n' for k, v in headers.items())
        try:
            res = subprocess.run(
                [curl, "-fsSL", "--max-time", "120", "-K", "-", url], input=config.encode(), capture_output=True
            )
        except OSError as exc:
            raise RoleInstallError(f"could not download {label}: {exc}") from exc
        if res.returncode != 0:
            raise RoleInstallError(f"could not download {label}: {res.stderr.decode(errors='replace').strip()}")
        return res.stdout
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=120) as resp:
            return resp.read()
    except OSError as exc:  # URLError and HTTPError are OSErrors
        raise RoleInstallError(f"could not download {label}: {exc}") from exc


def _safe_extract(data: bytes, dest: Path) -> None:
    """Extract regular files and directories only, refusing paths that leave ``dest``."""
    base = dest.resolve()
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for member in archive.getmembers():
            target = (dest / member.name).resolve()
            if base not in target.parents and target != base:
                raise RoleInstallError(f"unsafe path in archive: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                src = archive.extractfile(member)
                if src is not None:
                    target.write_bytes(src.read())


# --- parsing upstream files ---------------------------------------------------------------------

_URI_RE = re.compile(r"""^\s*-\s*uri:\s*["']?([^"'\s#]+)""", re.MULTILINE)
_DESC_RE = re.compile(r"""^description:\s*["']?(.*?)["']?\s*$""", re.MULTILINE)


def _split_gh(uri: str) -> tuple[str, str, str] | None:
    """``gh://owner/repo/path[@ref][?token=X]`` -> ``(owner/repo, path, ref)``; ``None`` otherwise."""
    if not uri.startswith("gh://"):
        return None
    body = uri[len("gh://"):].split("?", 1)[0]
    body, _, ref = body.partition("@")
    parts = body.strip("/").split("/")
    if len(parts) < 3:
        return None
    return f"{parts[0]}/{parts[1]}", "/".join(parts[2:]), ref or "HEAD"


def _skill_dir(root: Path, path: str) -> Path | None:
    for candidate in (root / path, root / "skills" / path):
        if (candidate / "SKILL.md").is_file():
            return candidate
    return None


def _licence_file(root: Path) -> Path | None:
    return next((root / n for n in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING") if (root / n).is_file()), None)


# --- install ------------------------------------------------------------------------------------


def available_roles(team_root: Path) -> list[str]:
    tdir = team_root / "templates"
    return sorted(d.name for d in tdir.iterdir() if (d / "scion-agent.yaml").is_file()) if tdir.is_dir() else []


def install_roles(
    project_dir: Path,
    roles: list[str] | None = None,
    privacy: str = "confidential",
    mirror: Path | None = None,
    ref: str = UPSTREAM_REF,
    force: bool = False,
) -> list[InstallResult]:
    """Install role templates into ``<project>/.scion/templates/tk-<role>/``.

    Existing generated templates are kept unless ``force``; a same-named template without
    ``UPSTREAM.md`` (hand-made) is never overwritten. Raises ``RoleInstallError`` on fetch errors
    or unknown roles before writing anything.
    """
    wanted = list(dict.fromkeys(roles or DEFAULT_ROLES))
    templates_root = project_dir / ".scion" / "templates"
    with tempfile.TemporaryDirectory(prefix="tk-roles-") as tmp:
        sources = _Sources(Path(tmp), mirror)
        team_root = sources.tree(UPSTREAM_REPO, ref)
        team_ref = sources.refs[f"{UPSTREAM_REPO}@{ref}"]
        known = available_roles(team_root)
        unknown = [r for r in wanted if r not in known]
        if unknown:
            raise RoleInstallError(f"unknown role(s): {', '.join(unknown)}. Available: {', '.join(known)}")

        results: list[InstallResult] = []
        for role in wanted:
            target = templates_root / template_name(role)
            if target.exists() and not (target / MARKER).exists():
                raise RoleInstallError(f"{target} exists and was not generated by tk; rename it or pick another role")
            if target.exists() and not force:
                results.append(InstallResult(role, target, "kept"))
                continue
            staged = Path(tmp) / f"stage-{role}"
            result = _build_role(staged, team_root, team_ref, role, privacy, sources)
            existed = target.exists()
            if existed:
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(staged), str(target))
            result.template_dir = target
            result.action = "updated" if existed else "installed"
            results.append(result)
        return results


def _build_role(
    out: Path, team_root: Path, team_ref: str, role: str, privacy: str, sources: _Sources
) -> InstallResult:
    src = team_root / "templates" / role
    manifest = (src / "scion-agent.yaml").read_text(encoding="utf-8")
    desc_match = _DESC_RE.search(manifest)
    description = (desc_match.group(1) if desc_match else f"agent-team role {role}").replace('"', "'")
    out.mkdir(parents=True)
    result = InstallResult(role, out, "installed")
    rows: list[str] = []

    skills_dir = out / "skills"
    for uri in _URI_RE.findall(manifest):
        parsed = _split_gh(uri)
        name = (parsed[1] if parsed else uri).rstrip("/").rsplit("/", 1)[-1]
        if privacy == "confidential" and name in PUBLISHING_SKILLS:
            result.dropped.append(name)
            rows.append(f"| {name} | `{uri}` | dropped: {PUBLISHING_SKILLS[name]} (privacy: confidential) |")
            continue
        if parsed is None:
            result.dropped.append(name)
            rows.append(f"| {name} | `{uri}` | dropped: only gh:// skills can be vendored |")
            continue
        repo, path, sref = parsed
        try:
            root = sources.tree(repo, sref)
        except RoleInstallError as exc:
            result.dropped.append(name)
            rows.append(f"| {name} | `{uri}` | dropped: {exc} |")
            continue
        sdir = _skill_dir(root, path)
        if sdir is None:
            result.dropped.append(name)
            rows.append(f"| {name} | `{uri}` | dropped: no SKILL.md found |")
            continue
        dest = skills_dir / name
        shutil.copytree(sdir, dest, symlinks=False)
        lic = _licence_file(root)
        if lic and _licence_file(dest) is None:
            shutil.copy2(lic, dest / "LICENSE")
        result.skills.append(name)
        rows.append(f"| {name} | `{uri}` @ {sources.refs[f'{repo}@{sref}']} | vendored |")

    upstream_agents = (src / "agents.md").read_text(encoding="utf-8") if (src / "agents.md").is_file() else ""
    (out / "agents.md").write_text(TK_CONTRACT.format(role=role) + upstream_agents, encoding="utf-8")
    if (src / "system-prompt.md").is_file():
        shutil.copy2(src / "system-prompt.md", out / "system-prompt.md")
    else:
        (out / "system-prompt.md").write_text(f"# {role}\n", encoding="utf-8")
    lic = _licence_file(team_root)
    if lic:
        shutil.copy2(lic, out / "LICENSE")
    (out / "scion-agent.yaml").write_text(
        f"# {template_name(role)}: agent-team role `{role}` for the tk task force (sources in {MARKER}).\n"
        "# Skills are vendored in skills/; nothing is fetched when a worker starts. Per Scion's template\n"
        "# rules, harness and model are not set here (they come from scion-taskforce.yaml).\n"
        'schema_version: "1"\n'
        f'description: "{description}"\n'
        "agent_instructions: agents.md\n"
        "system_prompt: system-prompt.md\n",
        encoding="utf-8",
    )
    source_url = (
        f"https://github.com/{UPSTREAM_REPO}/tree/{team_ref}/templates/{role}"
        if not team_ref.startswith("local copy") else f"{team_ref}/templates/{role}"
    )
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    (out / MARKER).write_text(
        f"# {template_name(role)}\n\n"
        f"Generated by `tk scion-taskforce templates install` on {stamp}. "
        "`templates install --force` regenerates this folder and discards local edits.\n\n"
        "| Item | Value |\n|---|---|\n"
        f"| Source | {source_url} |\n"
        "| Licence | Apache-2.0 (agent-team, see LICENSE); each vendored skill keeps its own LICENSE |\n"
        f"| Privacy | {privacy} |\n"
        "| Changes | `agents.md` starts with the tk contract; skills are vendored, `uri:` entries removed |\n\n"
        "## Skills\n\n| Skill | Source | Status |\n|---|---|---|\n"
        + ("\n".join(rows) + "\n" if rows else "| (none) | | |\n"),
        encoding="utf-8",
    )
    return result

