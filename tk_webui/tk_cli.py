import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import yaml

from .models import Ticket, NoteItem, DirectoryBrowseItem


def find_tk_binary() -> str:
    """Find the path to the tk binary."""
    which_tk = shutil.which("tk")
    if which_tk:
        return which_tk
    common_paths = [
        "/opt/homebrew/bin/tk",
        "/usr/local/bin/tk",
        os.path.expanduser("~/.local/bin/tk"),
        os.path.expanduser("~/bin/tk"),
    ]
    for p in common_paths:
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    return "tk"


TK_BIN = find_tk_binary()


def find_tickets_dir(base_dir: str) -> Optional[Path]:
    """Search for .tickets directory in base_dir or its parents."""
    current = Path(os.path.expanduser(base_dir)).resolve()
    while True:
        candidate = current / ".tickets"
        if candidate.is_dir():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def parse_ticket_markdown(file_path: Path) -> Optional[Ticket]:
    """Parse a single ticket .md file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return None

    # Frontmatter regex
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not fm_match:
        return None

    yaml_str = fm_match.group(1)
    body = fm_match.group(2).strip()

    try:
        meta = yaml.safe_load(yaml_str) or {}
    except Exception:
        meta = {}

    ticket_id = meta.get("id") or file_path.stem
    status = str(meta.get("status", "open"))
    ticket_type = str(meta.get("type", "task"))
    priority = str(meta.get("priority", "2"))
    assignee = meta.get("assignee")
    tags = meta.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    deps = meta.get("deps", [])
    if not isinstance(deps, list):
        deps = [deps] if deps else []
    links = meta.get("links", [])
    if not isinstance(links, list):
        links = [links] if links else []
    created_val = meta.get("created")
    created = str(created_val.isoformat()) if hasattr(created_val, "isoformat") else (str(created_val) if created_val else None)
    parent = meta.get("parent")
    external_ref = meta.get("external_ref")

    # Extract title from first # Title
    title = ticket_id
    title_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()
        # remove the title line from body
        body_without_title = body[:title_match.start()] + body[title_match.end():]
    else:
        body_without_title = body

    # Split sections in body: Description, ## Notes, ## Design, ## Acceptance Criteria
    sections = re.split(r"(?m)^##\s+", body_without_title)
    
    description = sections[0].strip() if sections else ""
    design = None
    acceptance = None
    notes: List[NoteItem] = []

    for s in sections[1:]:
        lines = s.split("\n", 1)
        sec_title = lines[0].strip().lower()
        sec_content = lines[1].strip() if len(lines) > 1 else ""

        if "design" in sec_title:
            design = sec_content
        elif "acceptance" in sec_title:
            acceptance = sec_content
        elif "notes" in sec_title:
            # Parse timestamped notes: **YYYY-MM-DD...** \n note content
            note_blocks = re.split(r"(?m)^\*\*([^*]+)\*\*", sec_content)
            # note_blocks[0] is text before first timestamp (usually empty)
            i = 1
            while i < len(note_blocks):
                ts = note_blocks[i].strip()
                n_text = note_blocks[i+1].strip() if i+1 < len(note_blocks) else ""
                notes.append(NoteItem(timestamp=ts, text=n_text))
                i += 2

    return Ticket(
        id=ticket_id,
        title=title,
        status=status,
        type=ticket_type,
        priority=priority,
        assignee=assignee,
        tags=tags,
        created=created,
        deps=[str(d) for d in deps],
        links=[str(l) for l in links],
        parent=parent,
        external_ref=external_ref,
        description=description,
        design=design,
        acceptance=acceptance,
        notes=notes,
        raw_body=body,
        file_path=str(file_path),
    )


def get_all_tickets(directory: str) -> List[Ticket]:
    """Retrieve all tickets in a directory and calculate blocked statuses."""
    tickets_dir = find_tickets_dir(directory)
    if not tickets_dir or not tickets_dir.exists():
        return []

    tickets: List[Ticket] = []
    ticket_map: Dict[str, Ticket] = {}

    for md_file in sorted(tickets_dir.glob("*.md")):
        if md_file.name.startswith("."):
            continue
        ticket = parse_ticket_markdown(md_file)
        if ticket:
            tickets.append(ticket)
            ticket_map[ticket.id] = ticket

    # Calculate blocked status: if any dep is not 'closed', the ticket is blocked
    for ticket in tickets:
        blocked_by = []
        for dep_id in ticket.deps:
            dep_ticket = ticket_map.get(dep_id)
            if dep_ticket and dep_ticket.status != "closed":
                blocked_by.append(dep_id)
            elif not dep_ticket:
                # If dependency ID isn't found or open elsewhere, consider it unresolved
                blocked_by.append(dep_id)
        if blocked_by:
            ticket.is_blocked = True
            ticket.blocked_by = blocked_by

    return tickets


def run_tk_cmd(directory: str, args: List[str]) -> Tuple[int, str, str]:
    """Run a tk command within the specified directory."""
    resolved_dir = str(Path(os.path.expanduser(directory)).resolve())
    cmd = [TK_BIN] + args
    env = os.environ.copy()
    
    try:
        proc = subprocess.run(
            cmd,
            cwd=resolved_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def create_ticket_cli(
    directory: str,
    title: str,
    description: Optional[str] = None,
    ticket_type: str = "task",
    priority: int = 2,
    assignee: Optional[str] = None,
    tags: Optional[List[str]] = None,
    design: Optional[str] = None,
    acceptance: Optional[str] = None,
    parent: Optional[str] = None,
    external_ref: Optional[str] = None,
) -> Tuple[bool, str]:
    """Create a ticket via `tk create`."""
    args = ["create", title]
    if description:
        args.extend(["-d", description])
    if ticket_type:
        args.extend(["-t", ticket_type])
    if priority is not None:
        args.extend(["-p", str(priority)])
    if assignee:
        args.extend(["-a", assignee])
    if tags:
        args.extend(["--tags", ",".join(tags)])
    if design:
        args.extend(["--design", design])
    if acceptance:
        args.extend(["--acceptance", acceptance])
    if parent:
        args.extend(["--parent", parent])
    if external_ref:
        args.extend(["--external-ref", external_ref])

    code, stdout, stderr = run_tk_cmd(directory, args)
    if code == 0:
        ticket_id = stdout.strip()
        return True, ticket_id
    return False, stderr or stdout


def update_ticket_content_cli(
    directory: str,
    ticket_id: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    ticket_type: Optional[str] = None,
    priority: Optional[int] = None,
    assignee: Optional[str] = None,
    tags: Optional[List[str]] = None,
    design: Optional[str] = None,
    acceptance: Optional[str] = None,
    parent: Optional[str] = None,
    external_ref: Optional[str] = None,
) -> Tuple[bool, str]:
    """Update ticket fields via `tk update` or direct file rewrite."""
    args = ["update", ticket_id]
    if title is not None:
        args.extend(["--title", title])
    if description is not None:
        args.extend(["-d", description])
    if ticket_type is not None:
        args.extend(["-t", ticket_type])
    if priority is not None:
        args.extend(["-p", str(priority)])
    if assignee is not None:
        args.extend(["-a", assignee])
    if tags is not None:
        args.extend(["--tags", ",".join(tags)])
    if design is not None:
        args.extend(["--design", design])
    if acceptance is not None:
        args.extend(["--acceptance", acceptance])
    if parent is not None:
        args.extend(["--parent", parent])
    if external_ref is not None:
        args.extend(["--external-ref", external_ref])

    code, stdout, stderr = run_tk_cmd(directory, args)
    if code == 0:
        return True, stdout
    return False, stderr or stdout


def update_ticket_status_cli(directory: str, ticket_id: str, new_status: str) -> Tuple[bool, str]:
    """Update status of a ticket."""
    if new_status == "in_progress":
        args = ["start", ticket_id]
    elif new_status == "closed":
        args = ["close", ticket_id]
    elif new_status == "open":
        args = ["reopen", ticket_id]
    else:
        args = ["status", ticket_id, new_status]

    code, stdout, stderr = run_tk_cmd(directory, args)
    if code == 0:
        return True, stdout
    return False, stderr or stdout


def add_note_cli(directory: str, ticket_id: str, note: str) -> Tuple[bool, str]:
    """Add note/comment to a ticket."""
    args = ["add-note", ticket_id, note]
    code, stdout, stderr = run_tk_cmd(directory, args)
    if code == 0:
        return True, stdout
    return False, stderr or stdout


def add_dep_cli(directory: str, ticket_id: str, dep_id: str) -> Tuple[bool, str]:
    """Add dependency."""
    args = ["dep", ticket_id, dep_id]
    code, stdout, stderr = run_tk_cmd(directory, args)
    if code == 0:
        return True, stdout
    return False, stderr or stdout


def remove_dep_cli(directory: str, ticket_id: str, dep_id: str) -> Tuple[bool, str]:
    """Remove dependency."""
    args = ["undep", ticket_id, dep_id]
    code, stdout, stderr = run_tk_cmd(directory, args)
    if code == 0:
        return True, stdout
    return False, stderr or stdout


def init_tickets_dir(directory: str) -> Tuple[bool, str]:
    """Initialize a .tickets repository by creating an initial setup ticket."""
    resolved = Path(os.path.expanduser(directory)).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    return create_ticket_cli(
        directory=str(resolved),
        title="Initialize Project Tickets",
        description="Ticket repository initialized via tk-webui",
        ticket_type="task",
        priority=3,
        tags=["meta", "setup"],
    )


def browse_path(path_str: str) -> List[DirectoryBrowseItem]:
    """List subdirectories of a given path for folder picker."""
    p = Path(os.path.expanduser(path_str)).resolve()
    if not p.exists() or not p.is_dir():
        p = Path.home()

    items: List[DirectoryBrowseItem] = []
    try:
        for entry in sorted(p.iterdir()):
            if entry.name.startswith(".") and entry.name != ".tickets":
                continue
            if entry.is_dir():
                has_tk = (entry / ".tickets").is_dir()
                items.append(
                    DirectoryBrowseItem(
                        name=entry.name,
                        path=str(entry),
                        is_dir=True,
                        has_tickets=has_tk,
                    )
                )
    except PermissionError:
        pass

    return items
