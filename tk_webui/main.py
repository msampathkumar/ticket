import os
import argparse
from pathlib import Path
from typing import List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from .models import (
    DirectoryCheckResponse,
    Ticket,
    TicketCreateRequest,
    TicketUpdateRequest,
    TicketStatusUpdateRequest,
    TicketAddNoteRequest,
    TicketDependencyRequest,
    DirectoryBrowseItem,
)
from .tk_cli import (
    find_tickets_dir,
    get_all_tickets,
    create_ticket_cli,
    update_ticket_content_cli,
    update_ticket_status_cli,
    add_note_cli,
    add_dep_cli,
    remove_dep_cli,
    init_tickets_dir,
    browse_path,
)

app = FastAPI(title="tk Web UI", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = Path(__file__).parent / "static"


@app.get("/api/check-directory", response_model=DirectoryCheckResponse)
def check_directory(path: str = Query(..., description="Directory path to inspect")):
    p = Path(os.path.expanduser(path)).resolve()
    exists = p.exists() and p.is_dir()
    tickets_dir = find_tickets_dir(str(p)) if exists else None
    has_tickets = tickets_dir is not None and tickets_dir.exists()
    ticket_count = 0
    if has_tickets:
        ticket_count = len(list(tickets_dir.glob("*.md")))

    return DirectoryCheckResponse(
        path=str(p),
        exists=exists,
        has_tickets=has_tickets,
        tickets_dir=str(tickets_dir) if tickets_dir else None,
        ticket_count=ticket_count,
    )


@app.get("/api/browse", response_model=List[DirectoryBrowseItem])
def browse_directory(path: str = Query("~", description="Base directory to browse")):
    return browse_path(path)


@app.get("/api/tickets", response_model=List[Ticket])
def list_tickets(directory: str = Query(..., description="Project directory")):
    p = Path(os.path.expanduser(directory)).resolve()
    if not p.exists():
        raise HTTPException(status_code=404, detail="Directory not found")
    tickets = get_all_tickets(str(p))
    return tickets


@app.post("/api/tickets")
def create_ticket(req: TicketCreateRequest):
    success, result = create_ticket_cli(
        directory=req.directory,
        title=req.title,
        description=req.description,
        ticket_type=req.type,
        priority=req.priority,
        assignee=req.assignee,
        tags=req.tags,
        design=req.design,
        acceptance=req.acceptance,
        parent=req.parent,
        external_ref=req.external_ref,
    )
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", "ticket_id": result}


@app.put("/api/tickets")
def update_ticket(req: TicketUpdateRequest):
    success, message = update_ticket_content_cli(
        directory=req.directory,
        ticket_id=req.ticket_id,
        title=req.title,
        description=req.description,
        ticket_type=req.type,
        priority=req.priority,
        assignee=req.assignee,
        tags=req.tags,
        design=req.design,
        acceptance=req.acceptance,
        parent=req.parent,
        external_ref=req.external_ref,
    )
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message}


@app.put("/api/tickets/status")
def update_status(req: TicketStatusUpdateRequest):
    success, message = update_ticket_status_cli(req.directory, req.ticket_id, req.status)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message}


@app.post("/api/tickets/notes")
def add_note(req: TicketAddNoteRequest):
    if not req.note.strip():
        raise HTTPException(status_code=400, detail="Note text cannot be empty")
    success, message = add_note_cli(req.directory, req.ticket_id, req.note)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message}


@app.post("/api/tickets/dependencies")
def add_dependency(req: TicketDependencyRequest):
    success, message = add_dep_cli(req.directory, req.ticket_id, req.dep_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message}


@app.delete("/api/tickets/dependencies")
def remove_dependency(req: TicketDependencyRequest):
    success, message = remove_dep_cli(req.directory, req.ticket_id, req.dep_id)
    if not success:
        raise HTTPException(status_code=400, detail=message)
    return {"status": "ok", "message": message}


@app.post("/api/init")
def initialize_tickets(directory: str = Body(..., embed=True)):
    success, result = init_tickets_dir(directory)
    if not success:
        raise HTTPException(status_code=400, detail=result)
    return {"status": "ok", "message": "Tickets repository initialized", "ticket_id": result}


if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"message": "tk-webui backend is running. Frontend not found."})


def main():
    import sys
    if "--tk-describe" in sys.argv:
        print("tk-plugin: Interactive Kanban Web UI & PR review dashboard")
        return

    parser = argparse.ArgumentParser(description="tk Web UI Server")
    parser.add_argument("directory", nargs="?", default=os.getcwd(), help="Initial directory to open")
    parser.add_argument("--host", default="127.0.0.1", help="Host address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Auto-reload on code change")
    parser.add_argument("--tk-describe", action="store_true", help="Print plugin description for tk CLI")
    args = parser.parse_args()

    os.environ["INITIAL_PROJECT_DIR"] = os.path.abspath(os.path.expanduser(args.directory))
    print(f"🚀 Starting tk-webui on http://{args.host}:{args.port}")
    print(f"📁 Initial directory: {os.environ['INITIAL_PROJECT_DIR']}")
    uvicorn.run("tk_webui.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
