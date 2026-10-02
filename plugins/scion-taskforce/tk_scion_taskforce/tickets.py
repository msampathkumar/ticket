"""Ticket discovery, frontmatter parser, and safe mutation helpers for tk-scion-taskforce."""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

TICKET_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")


@dataclass
class TicketInfo:
    id: str
    path: Path
    project_dir: Path
    title: str
    status: str = "open"
    priority: int = 2
    ticket_type: str = "task"
    deps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    closed: str | None = None
    external_ref: str = ""  # e.g. gh-pr-123 / gh-123 / JIRA-1 (from tk --external-ref)
    body: str = ""
    notes: list[tuple[str, str]] = field(default_factory=list)  # (timestamp, note_text)

    @property
    def last_note_hash(self) -> str:
        if not self.notes:
            return ""
        ts, text = self.notes[-1]
        return hashlib.sha256(f"{ts}:{text}".encode()).hexdigest()[:16]


def validate_ticket_id(ticket_id: str) -> str:
    clean = ticket_id.strip()
    if not clean or not TICKET_ID_RE.match(clean):
        raise ValueError(f"Invalid ticket ID: {ticket_id!r}")
    return clean


def get_tickets_dir(project_dir: Path) -> Path:
    resolved_proj = Path(project_dir).expanduser().resolve()
    if resolved_proj.name == ".tickets":
        return resolved_proj
    return resolved_proj / ".tickets"


def resolve_ticket_path(project_dir: Path, ticket_id: str) -> Path | None:
    clean_id = validate_ticket_id(ticket_id)
    tickets_dir = get_tickets_dir(project_dir).resolve()
    if not tickets_dir.exists():
        return None

    exact = (tickets_dir / f"{clean_id}.md").resolve()
    if exact.parent == tickets_dir and exact.exists():
        return exact

    matches = []
    for p in sorted(tickets_dir.glob("*.md")):
        resolved_p = p.resolve()
        if resolved_p.parent == tickets_dir and clean_id in resolved_p.stem:
            matches.append(resolved_p)
    if len(matches) == 1:
        return matches[0]
    return None


def _parse_list_field(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        inner = raw[1:-1].strip()
        if not inner:
            return []
        return [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
    if not raw:
        return []
    return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]


def parse_ticket_file(ticket_path: Path, project_dir: Path | None = None) -> TicketInfo:
    resolved_path = ticket_path.expanduser().resolve()
    proj = (project_dir or resolved_path.parent.parent).expanduser().resolve()
    text = resolved_path.read_text(encoding="utf-8")

    frontmatter: dict[str, str] = {}
    body = text
    if text.startswith("---\n"):
        end_idx = text.find("\n---\n", 4)
        if end_idx != -1:
            fm_block = text[4:end_idx]
            body = text[end_idx + 5 :]
            for line in fm_block.splitlines():
                if ":" in line:
                    k, _, v = line.partition(":")
                    frontmatter[k.strip()] = v.strip()

    ticket_id = frontmatter.get("id", resolved_path.stem)
    status = frontmatter.get("status", "open")
    try:
        priority = int(frontmatter.get("priority", "2"))
    except ValueError:
        priority = 2
    ticket_type = frontmatter.get("type", "task")
    deps = _parse_list_field(frontmatter.get("deps", "[]"))
    tags = _parse_list_field(frontmatter.get("tags", "[]"))
    closed = frontmatter.get("closed") or None
    external_ref = (frontmatter.get("external-ref") or frontmatter.get("external_ref") or "").strip()

    title = ticket_id
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break

    notes: list[tuple[str, str]] = []
    if "## Notes" in body:
        _, _, notes_section = body.partition("## Notes")
        current_ts: str | None = None
        current_lines: list[str] = []
        for line in notes_section.splitlines():
            if line.startswith("**") and line.endswith("**") and len(line) > 4:
                if current_ts is not None:
                    notes.append((current_ts, "\n".join(current_lines).strip()))
                current_ts = line.strip("*").strip()
                current_lines = []
            elif current_ts is not None:
                current_lines.append(line)
        if current_ts is not None:
            notes.append((current_ts, "\n".join(current_lines).strip()))

    return TicketInfo(
        id=ticket_id,
        path=resolved_path,
        project_dir=proj,
        title=title,
        status=status,
        priority=priority,
        ticket_type=ticket_type,
        deps=deps,
        tags=tags,
        closed=closed,
        external_ref=external_ref,
        body=body.strip(),
        notes=notes,
    )


def load_all_tickets(project_dir: Path) -> dict[str, TicketInfo]:
    tickets_dir = get_tickets_dir(project_dir)
    if not tickets_dir.exists():
        return {}
    result: dict[str, TicketInfo] = {}
    for md_path in sorted(tickets_dir.glob("*.md")):
        if md_path.name.startswith("."):
            continue
        info = parse_ticket_file(md_path, project_dir=project_dir)
        result[info.id] = info
    return result


def get_ready_tickets(project_dir: Path) -> list[TicketInfo]:
    """Return unblocked tickets (open or in_progress with all deps closed), sorted by priority & id."""
    all_tickets = load_all_tickets(project_dir)
    ready: list[TicketInfo] = []
    for t in all_tickets.values():
        if t.status not in ("open", "in_progress"):
            continue
        unblocked = True
        for dep_id in t.deps:
            dep_ticket = all_tickets.get(dep_id)
            if dep_ticket is None or dep_ticket.status != "closed":
                unblocked = False
                break
        if unblocked:
            ready.append(t)
    ready.sort(key=lambda item: (item.priority, item.id))
    return ready


def update_ticket_frontmatter(
    ticket_path: Path,
    status: str | None = None,
    tags: list[str] | None = None,
) -> None:
    """Safely update status and/or tags in a ticket markdown file's YAML frontmatter."""
    resolved_path = ticket_path.expanduser().resolve()
    text = resolved_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return
    end_idx = text.find("\n---\n", 4)
    if end_idx == -1:
        return

    fm_lines = text[4:end_idx].splitlines()
    rest = text[end_idx + 5 :]

    has_status = False
    has_tags = False
    new_lines: list[str] = []

    for line in fm_lines:
        key, sep, _ = line.partition(":")
        k = key.strip()
        if sep and k == "status" and status is not None:
            new_lines.append(f"status: {status}")
            has_status = True
        elif sep and k == "tags" and tags is not None:
            formatted_tags = ", ".join(tags)
            new_lines.append(f"tags: [{formatted_tags}]")
            has_tags = True
        else:
            new_lines.append(line)

    if status is not None and not has_status:
        new_lines.append(f"status: {status}")
    if tags is not None and not has_tags:
        formatted_tags = ", ".join(tags)
        new_lines.append(f"tags: [{formatted_tags}]")

    updated = "---\n" + "\n".join(new_lines) + "\n---\n" + rest
    resolved_path.write_text(updated, encoding="utf-8")


def add_ticket_tag(ticket_path: Path, tag: str) -> list[str]:
    info = parse_ticket_file(ticket_path)
    tags = list(info.tags)
    if tag not in tags:
        tags.append(tag)
        update_ticket_frontmatter(ticket_path, tags=tags)
    return tags


def remove_ticket_tag(ticket_path: Path, tag: str) -> list[str]:
    info = parse_ticket_file(ticket_path)
    tags = [t for t in info.tags if t != tag]
    if len(tags) != len(info.tags):
        update_ticket_frontmatter(ticket_path, tags=tags)
    return tags


def append_ticket_note(ticket_path: Path, note_text: str) -> str:
    """Append a timestamped note to the ticket's ## Notes section (matches 'tk add-note')."""
    resolved_path = ticket_path.expanduser().resolve()
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    content = resolved_path.read_text(encoding="utf-8")

    if "## Notes" not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n## Notes\n"

    if not content.endswith("\n"):
        content += "\n"
    content += f"\n**{timestamp}**\n\n{note_text.strip()}\n"
    resolved_path.write_text(content, encoding="utf-8")
    return timestamp


def append_raw_note(ticket_path: Path, timestamp: str, note_text: str) -> None:
    """Append a note block with a caller-supplied timestamp (used when mirroring worker notes)."""
    resolved_path = ticket_path.expanduser().resolve()
    content = resolved_path.read_text(encoding="utf-8")
    if "## Notes" not in content:
        if not content.endswith("\n"):
            content += "\n"
        content += "\n## Notes\n"
    if not content.endswith("\n"):
        content += "\n"
    content += f"\n**{timestamp}**\n\n{note_text.strip()}\n"
    resolved_path.write_text(content, encoding="utf-8")


def merge_worker_ticket_copy(main_path: Path, worker_copy: Path, review_tag: str) -> dict[str, int]:
    """Merge a worker's edited copy of a ticket (from its isolated workspace) into the project ticket.

    Only *additive* signals flow back: notes the main ticket does not have yet (matched by
    timestamp + text) and the review tag. Status/title/body edits by the worker are ignored so a
    worker can never close or rewrite a ticket. Returns counters for logging.
    """
    result = {"notes": 0, "review_tag": 0}
    if not worker_copy.is_file() or not main_path.is_file():
        return result
    main = parse_ticket_file(main_path)
    copy = parse_ticket_file(worker_copy, project_dir=main.project_dir)
    have = {(ts, txt) for ts, txt in main.notes}
    for ts, txt in copy.notes:
        if (ts, txt) not in have:
            append_raw_note(main_path, ts, txt)
            result["notes"] += 1
    if review_tag in copy.tags and review_tag not in main.tags:
        add_ticket_tag(main_path, review_tag)
        result["review_tag"] = 1
    return result


def find_tk_binary(project_dir: Path | None = None) -> str | None:
    tk_script = os.environ.get("TK_SCRIPT")
    if tk_script and os.path.isfile(tk_script) and os.access(tk_script, os.X_OK):
        return tk_script
    if project_dir is not None:
        local_ticket = Path(project_dir).expanduser().resolve() / "ticket"
        if local_ticket.is_file() and os.access(local_ticket, os.X_OK):
            return str(local_ticket)
    repo_root_ticket = Path(__file__).resolve().parents[3] / "ticket"
    if repo_root_ticket.is_file() and os.access(repo_root_ticket, os.X_OK):
        return str(repo_root_ticket)
    for candidate in ("tk", "ticket"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def run_tk_show(project_dir: Path, ticket_id: str) -> str:
    clean_id = validate_ticket_id(ticket_id)
    tk_bin = find_tk_binary(project_dir)
    tickets_dir = get_tickets_dir(project_dir)
    if tk_bin:
        env = os.environ.copy()
        env["TICKETS_DIR"] = str(tickets_dir)
        res = subprocess.run(
            [tk_bin, "super", "show", clean_id],
            cwd=str(project_dir),
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout
    t_path = resolve_ticket_path(project_dir, clean_id)
    if t_path and t_path.exists():
        return t_path.read_text(encoding="utf-8")
    return ""
