from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DirectoryCheckResponse(BaseModel):
    path: str
    exists: bool
    has_tickets: bool
    tickets_dir: Optional[str] = None
    ticket_count: int = 0
    recent_directories: List[str] = []


class NoteItem(BaseModel):
    timestamp: str
    text: str


class Ticket(BaseModel):
    id: str
    title: str
    status: str = "open"  # open, in_progress, closed
    type: str = "task"    # bug, feature, task, epic, chore
    priority: str = "2"   # 0, 1, 2, 3, 4
    assignee: Optional[str] = None
    tags: List[str] = []
    created: Optional[str] = None
    deps: List[str] = []
    links: List[str] = []
    parent: Optional[str] = None
    external_ref: Optional[str] = None
    description: Optional[str] = None
    design: Optional[str] = None
    acceptance: Optional[str] = None
    notes: List[NoteItem] = []
    raw_body: Optional[str] = None
    is_blocked: bool = False
    blocked_by: List[str] = []
    file_path: Optional[str] = None


class TicketCreateRequest(BaseModel):
    directory: str
    title: str
    description: Optional[str] = None
    type: str = "task"
    priority: int = 2
    assignee: Optional[str] = None
    tags: Optional[List[str]] = None
    design: Optional[str] = None
    acceptance: Optional[str] = None
    parent: Optional[str] = None
    external_ref: Optional[str] = None


class TicketUpdateRequest(BaseModel):
    directory: str
    ticket_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[int] = None
    assignee: Optional[str] = None
    tags: Optional[List[str]] = None
    design: Optional[str] = None
    acceptance: Optional[str] = None
    parent: Optional[str] = None
    external_ref: Optional[str] = None


class TicketStatusUpdateRequest(BaseModel):
    directory: str
    ticket_id: str
    status: str  # open, in_progress, closed


class TicketAddNoteRequest(BaseModel):
    directory: str
    ticket_id: str
    note: str


class TicketDependencyRequest(BaseModel):
    directory: str
    ticket_id: str
    dep_id: str


class DirectoryBrowseItem(BaseModel):
    name: str
    path: str
    is_dir: bool
    has_tickets: bool
