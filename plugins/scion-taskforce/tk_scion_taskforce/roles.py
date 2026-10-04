"""Agent-team roles from scion-frontiers/agent-team, installed per project as skills with the tk contract on top.

`skills install` downloads upstream once at a pinned commit and writes one skill per role, plus every
skill the roles reference, into ``<project>/.agents/skills/tk-scion-<name>/`` (nothing is fetched when a
worker starts). Each generated folder records its sources in ``UPSTREAM.md``. Every ticket runs on the
one worker template; a ``role:<name>`` tag makes the brief name ``.agents/skills/tk-scion-<name>/SKILL.md``.

Template = how the pod runs; skill = how to do the job. The same skills work for humans and local agents.
"""

from __future__ import annotations

import io
import json
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
UPSTREAM_REF = "3650f1b03411116fcbf37852bfec6911db64b569"  # pinned; `skills install --ref <sha>` overrides
ROLE_TAG = "role:"
SKILL_PREFIX = "tk-scion-"  # every generated skill folder (and its SKILL.md `name:`) starts with this
SKILLS_DIR = Path(".agents") / "skills"  # project-relative
TEMPLATE_PREFIX = "tk-"  # deprecated: per-role templates `.scion/templates/tk-<role>/` (before skills)
MARKER = "UPSTREAM.md"  # marks a generated skill or role template (uninit and --force only touch these)
_ROLE_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")
# Installed when `skills install` gets no role names. Left out: coordinator and eng-manager
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

TK_CONTRACT = """## tk contract (wins over the role guidance below)

You own exactly one `tk` ticket. Your task brief holds its ID, its details and this project's rules for
git and confidentiality; where this skill and the brief disagree, the brief wins.

- Work alone. There is no coordinator, manager or other agent to message; the ticket is your only channel.
- Use `tk` for updates (check `command -v tk`). Read the ticket and new feedback with `tk show <id>`, again
  whenever you resume. Share progress and questions with `tk add-note <id> "..."`.
- Report with `tk add-note`: what you did, how you verified it and any open questions. Then add the review
  tag named in your brief (default `waiting-for-review`) with `tk update <id> --tags ...`, keeping the
  existing tags, and stop. Change only your own ticket; never close, reopen or create tickets.
- Follow the git rule in your brief. Never run `git init`. Never push unless the ticket asks for it.
- Where the role guidance says to message a coordinator, push to signal completion, or write to
  `.design/` or a project log, put that content in your ticket report instead.
- Do not publish or upload project content unless the ticket asks for it.
"""


class RoleInstallError(Exception):
    """Role skills could not be installed; nothing was changed."""


@dataclass
class InstallResult:
    role: str
    path: Path  # the role's skill folder
    action: str  # "installed" | "updated" | "kept"
    skills: list[str] = field(default_factory=list)  # referenced skills (unprefixed) the role skill points to
    dropped: list[str] = field(default_factory=list)


@dataclass
class RoleSelection:
    """How a ticket's ``role:<name>`` tags resolve in a project."""

    roles: list[str] = field(default_factory=list)  # every role tag, in order
    skills: list[str] = field(default_factory=list)  # roles with `.agents/skills/tk-scion-<role>/SKILL.md`
    template: str = ""  # deprecated: an old generated `tk-<role>` template for a role without a skill
    missing: list[str] = field(default_factory=list)  # roles with neither: the worker is not started


def skill_name(name: str) -> str:
    return f"{SKILL_PREFIX}{name}"


def skills_root(project_dir: Path) -> Path:
    return Path(project_dir) / SKILLS_DIR


def skill_rel_path(name: str) -> str:
    """Workspace-relative SKILL.md path for the unprefixed skill or role ``name``."""
    return f"{SKILLS_DIR.as_posix()}/{skill_name(name)}/SKILL.md"


def template_name(role: str) -> str:
    return f"{TEMPLATE_PREFIX}{role}"


def ticket_roles(tags: Iterable[str]) -> list[str]:
    """Every role named by a ``role:<name>`` tag, in order, without duplicates."""
    found = [str(t)[len(ROLE_TAG):].strip() for t in tags if str(t).startswith(ROLE_TAG)]
    return list(dict.fromkeys(r for r in found if r))


def select_roles(project_dir: Path, tags: Iterable[str]) -> RoleSelection:
    """Resolve a ticket's role tags: a role skill if installed, else (deprecated) an old ``tk-<role>``
    template (only one, since a worker runs on one template), else missing."""
    sel = RoleSelection(roles=ticket_roles(tags))
    for role in sel.roles:
        valid = bool(_ROLE_NAME_RE.fullmatch(role))
        if valid and (skills_root(project_dir) / skill_name(role) / "SKILL.md").is_file():
            sel.skills.append(role)
        # deprecated: old per-role templates keep working until removed; remove after 2027-04-01
        elif valid and not sel.template and (Path(project_dir) / ".scion" / "templates" / template_name(role)).is_dir():
            sel.template = template_name(role)
        else:
            sel.missing.append(role)
    return sel


def install_command(roles: Iterable[str]) -> str:
    return "tk scion-taskforce skills install " + " ".join(roles)


def installed_skills(project_dir: Path) -> list[tuple[str, str]]:
    """``(folder name, description)`` for every ``tk-scion-*`` skill in the project (generated or not)."""
    root = skills_root(project_dir)
    found = []
    for skill_md in sorted(root.glob(f"{SKILL_PREFIX}*/SKILL.md")):
        found.append((skill_md.parent.name, _frontmatter_field(skill_md.read_text(encoding="utf-8"), "description")))
    return found


def installed_role_skills(project_dir: Path) -> list[tuple[str, str]]:
    """``(role, source)`` for every generated role skill (its UPSTREAM.md has a ``| Role |`` row)."""
    found = []
    for marker in sorted(skills_root(project_dir).glob(f"{SKILL_PREFIX}*/{MARKER}")):
        rows = {ln.split("|")[1].strip(): ln.split("|")[2].strip()
                for ln in marker.read_text(encoding="utf-8").splitlines() if ln.startswith("| ") and ln.count("|") >= 3}
        if rows.get("Role"):
            found.append((rows["Role"], rows.get("Source", "")))
    return found


def selectable_skills(project_dir: Path) -> list[tuple[str, str]]:
    """Skills an untagged ticket's brief lists: generated role skills and hand-made ``tk-scion-*`` skills.
    Generated support skills are left out; the role skills point to them."""
    roles = {skill_name(r) for r, _ in installed_role_skills(project_dir)}
    root = skills_root(project_dir)
    return [(n, d) for n, d in installed_skills(project_dir) if n in roles or not (root / n / MARKER).exists()]


def installed_roles(project_dir: Path) -> list[tuple[str, str]]:
    """``(role, source line)`` for every generated (deprecated) role template in the project."""
    root = project_dir / ".scion" / "templates"
    found = []
    for marker in sorted(root.glob(f"{TEMPLATE_PREFIX}*/{MARKER}")):
        source = next((ln for ln in marker.read_text(encoding="utf-8").splitlines() if ln.startswith("| Source")), "")
        found.append((marker.parent.name[len(TEMPLATE_PREFIX):], source.split("|")[2].strip() if source else ""))
    return found


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


_FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.DOTALL)


def _frontmatter_field(text: str, key: str) -> str:
    """A top-level scalar from SKILL.md frontmatter, folded (``>``/``|``) values joined on one line."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return ""
    lines = match.group(1).splitlines()
    for i, line in enumerate(lines):
        if not line.startswith(f"{key}:"):
            continue
        value = line[len(key) + 1:].strip()
        if value in ("", ">", "|", ">-", "|-", ">+", "|+"):
            cont = []
            for nxt in lines[i + 1:]:
                if not nxt.startswith((" ", "\t")):
                    break
                cont.append(nxt.strip())
            value = " ".join(cont)
        return value.strip().strip("\"'")
    return ""


def _set_skill_name(text: str, name: str) -> str:
    """Set the frontmatter ``name:`` to ``name`` (adding frontmatter if there is none)."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return f"---\nname: {name}\n---\n\n{text}"
    front = match.group(1)
    if re.search(r"^name:", front, re.MULTILINE):
        front = re.sub(r"^name:.*$", f"name: {name}", front, count=1, flags=re.MULTILINE)
    else:
        front = f"name: {name}\n{front}"
    return f"---\n{front}\n---\n{text[match.end():]}"


def _demote_headings(markdown: str) -> str:
    """Push every Markdown heading two levels down (outside code fences, capped at ``######``) so
    upstream files nest under the role skill's own ``##`` sections."""
    out, fenced = [], False
    for line in markdown.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
        heading = None if fenced else re.match(r"(#{1,6}) ", line)
        out.append("#" * min(6, len(heading.group(1)) + 2) + line[len(heading.group(1)):] if heading else line)
    return "\n".join(out).strip() + "\n"


# --- install ------------------------------------------------------------------------------------


def available_roles(team_root: Path) -> list[str]:
    tdir = team_root / "templates"
    return sorted(d.name for d in tdir.iterdir() if (d / "scion-agent.yaml").is_file()) if tdir.is_dir() else []


def install_skills(
    project_dir: Path,
    roles: list[str] | None = None,
    privacy: str = "confidential",
    mirror: Path | None = None,
    ref: str = UPSTREAM_REF,
    force: bool = False,
) -> list[InstallResult]:
    """Install role skills (and the skills they reference) into ``<project>/.agents/skills/tk-scion-*/``.

    Existing generated skills are kept unless ``force``. A ``tk-scion-*`` folder without ``UPSTREAM.md``
    (hand-made) is never changed, and folders without the prefix are never touched. Everything is staged
    first, so a fetch error or unknown role raises ``RoleInstallError`` before anything is written.
    """
    wanted = list(dict.fromkeys(roles or DEFAULT_ROLES))
    root = skills_root(project_dir)
    with tempfile.TemporaryDirectory(prefix="tk-skills-") as tmp:
        sources = _Sources(Path(tmp), mirror)
        team_root = sources.tree(UPSTREAM_REPO, ref)
        team_ref = sources.refs[f"{UPSTREAM_REPO}@{ref}"]
        known = available_roles(team_root)
        unknown = [r for r in wanted if r not in known]
        if unknown:
            raise RoleInstallError(f"unknown role(s): {', '.join(unknown)}. Available: {', '.join(known)}")
        for role in wanted:
            target = root / skill_name(role)
            if target.exists() and not (target / MARKER).exists():
                raise RoleInstallError(f"{target} exists and was not generated by tk; rename it or pick another role")

        stage = Path(tmp) / "stage"
        stage.mkdir()
        ctx = _SkillBuild(stage, root, team_root, team_ref, privacy, sources, force, set(known))
        results: list[InstallResult] = []
        for role in wanted:
            target = root / skill_name(role)
            if target.exists() and not force:
                results.append(InstallResult(role, target, "kept"))
                continue
            result = _build_role_skill(ctx, role)
            result.action = "updated" if target.exists() else "installed"
            results.append(result)

        root.mkdir(parents=True, exist_ok=True)
        for staged in sorted(stage.iterdir()):
            target = root / staged.name
            if target.exists():
                shutil.rmtree(target)
            shutil.move(str(staged), str(target))
        if force and privacy == "confidential":
            for name in PUBLISHING_SKILLS:  # a refresh under confidential privacy removes old generated copies
                old = root / skill_name(name)
                if (old / MARKER).is_file():
                    shutil.rmtree(old)
        return results


@dataclass
class _SkillBuild:
    stage: Path
    root: Path  # the project's .agents/skills/
    team_root: Path
    team_ref: str
    privacy: str
    sources: _Sources
    force: bool
    role_names: set[str]
    # referenced skill -> (usable, description, UPSTREAM row status); each is resolved once per run
    done: dict[str, tuple[bool, str, str]] = field(default_factory=dict)


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _resolve_skill(ctx: _SkillBuild, uri: str) -> tuple[str, bool, str, str]:
    """Stage one referenced skill as ``tk-scion-<name>``. Returns ``(name, usable, description, status)``."""
    parsed = _split_gh(uri)
    name = (parsed[1] if parsed else uri).rstrip("/").rsplit("/", 1)[-1]
    if name in ctx.done:
        return (name, *ctx.done[name])
    existing = ctx.root / skill_name(name)
    if ctx.privacy == "confidential" and name in PUBLISHING_SKILLS:
        res = (False, "", f"dropped: {PUBLISHING_SKILLS[name]} (privacy: confidential)")
    elif not _ROLE_NAME_RE.fullmatch(name) or name in ctx.role_names:
        res = (False, "", "dropped: name clashes with an agent-team role or is not a valid folder name")
    elif parsed is None:
        res = (False, "", "dropped: only gh:// skills can be vendored")
    elif existing.is_dir() and (not (existing / MARKER).exists() or not ctx.force):
        desc = _frontmatter_field((existing / "SKILL.md").read_text(encoding="utf-8"), "description") \
            if (existing / "SKILL.md").is_file() else ""
        res = (True, desc, "kept (not generated by tk)" if not (existing / MARKER).exists() else "kept")
    else:
        repo, path, sref = parsed
        try:
            src_root = ctx.sources.tree(repo, sref)
        except RoleInstallError as exc:
            src_root, res = None, (False, "", f"dropped: {exc}")
        sdir = _skill_dir(src_root, path) if src_root is not None else None
        if src_root is not None and sdir is None:
            res = (False, "", "dropped: no SKILL.md found")
        elif sdir is not None:
            dest = ctx.stage / skill_name(name)
            shutil.copytree(sdir, dest, symlinks=False)
            skill_md = dest / "SKILL.md"
            text = _set_skill_name(skill_md.read_text(encoding="utf-8"), skill_name(name))
            skill_md.write_text(text, encoding="utf-8")
            lic = _licence_file(src_root)
            if lic and _licence_file(dest) is None:
                shutil.copy2(lic, dest / "LICENSE")
            source = f"`{uri}` @ {ctx.sources.refs[f'{repo}@{sref}']}"
            (dest / MARKER).write_text(
                f"# {skill_name(name)}\n\n"
                f"Generated by `tk scion-taskforce skills install` on {_stamp()}. "
                "`skills install --force` regenerates this folder and discards local edits.\n\n"
                "| Item | Value |\n|---|---|\n"
                f"| Source | {source} |\n"
                "| Licence | see LICENSE (from the source repository) |\n"
                f"| Changes | SKILL.md `name:` set to `{skill_name(name)}` |\n",
                encoding="utf-8",
            )
            res = (True, _frontmatter_field(text, "description"), f"vendored @ {ctx.sources.refs[f'{repo}@{sref}']}")
    ctx.done[name] = res
    return (name, *res)


def _build_role_skill(ctx: _SkillBuild, role: str) -> InstallResult:
    src = ctx.team_root / "templates" / role
    manifest = (src / "scion-agent.yaml").read_text(encoding="utf-8")
    desc_match = _DESC_RE.search(manifest)
    upstream_desc = (desc_match.group(1) if desc_match else f"agent-team role {role}").strip().rstrip(".")
    name = skill_name(role)
    out = ctx.stage / name
    out.mkdir(parents=True)
    result = InstallResult(role, ctx.root / name, "installed")
    rows: list[str] = []
    related: list[str] = []
    for uri in _URI_RE.findall(manifest):
        sname, usable, sdesc, status = _resolve_skill(ctx, uri)
        rows.append(f"| {sname} | `{uri}` | {status} |")
        if usable:
            result.skills.append(sname)
            related.append(f"- `{sname}`: `{skill_rel_path(sname)}`" + (f" ({sdesc})" if sdesc else ""))
        else:
            result.dropped.append(sname)

    persona = (src / "system-prompt.md").read_text(encoding="utf-8") if (src / "system-prompt.md").is_file() else ""
    guidance = (src / "agents.md").read_text(encoding="utf-8") if (src / "agents.md").is_file() else ""
    description = (
        f"{upstream_desc}. tk task force role `{role}` (agent-team): use it when a tk ticket is tagged "
        f"role:{role} or clearly asks for this kind of work."
    )
    parts = [
        f"---\nname: {name}\ndescription: {json.dumps(description, ensure_ascii=False)}\n---\n",
        f"# {name}: agent-team role `{role}` for tk tickets\n",
        f"Generated by `tk scion-taskforce skills install` from github.com/{UPSTREAM_REPO} (sources in "
        f"`{MARKER}`). Read it fully before you start work on the ticket.\n",
        TK_CONTRACT,
    ]
    if persona.strip():
        parts.append("## Persona (upstream `system-prompt.md`)\n\n" + _demote_headings(persona))
    if guidance.strip():
        parts.append("## Role guidance (upstream `agents.md`)\n\n" + _demote_headings(guidance))
    if related:
        parts.append(
            "## Related skills\n\nWhen the role guidance names one of these skills, read it from this project:\n"
            + "\n".join(related) + "\n"
        )
    if result.dropped:
        parts.append(f"Not available here: {', '.join(result.dropped)} (see `{MARKER}`).\n")
    (out / "SKILL.md").write_text("\n".join(parts), encoding="utf-8")

    lic = _licence_file(ctx.team_root)
    if lic:
        shutil.copy2(lic, out / "LICENSE")
    source_url = (
        f"https://github.com/{UPSTREAM_REPO}/tree/{ctx.team_ref}/templates/{role}"
        if not ctx.team_ref.startswith("local copy") else f"{ctx.team_ref}/templates/{role}"
    )
    (out / MARKER).write_text(
        f"# {name}\n\n"
        f"Generated by `tk scion-taskforce skills install` on {_stamp()}. "
        "`skills install --force` regenerates this folder and discards local edits.\n\n"
        "| Item | Value |\n|---|---|\n"
        f"| Role | {role} |\n"
        f"| Source | {source_url} |\n"
        "| Licence | Apache-2.0 (agent-team, see LICENSE); each referenced skill keeps its own LICENSE |\n"
        f"| Privacy | {ctx.privacy} |\n"
        "| Changes | SKILL.md = tk contract + upstream `system-prompt.md` (persona) + `agents.md`; "
        "referenced skills installed as `tk-scion-<name>`; per-role model and resource settings dropped |\n\n"
        "## Referenced skills\n\n| Skill | Source | Status |\n|---|---|---|\n"
        + ("\n".join(rows) + "\n" if rows else "| (none) | | |\n"),
        encoding="utf-8",
    )
    return result
