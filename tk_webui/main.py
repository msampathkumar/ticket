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


def print_version():
    print("""tk-webui version 0.2.0

Interactive Kanban Web UI & PR review dashboard for tk.
Created by Sampath Kumar & wedow contributors
GitHub: https://github.com/msampathkumar/ticket
License: MIT

Thank you for using tk! If you find it helpful, please star the repo or contribute on GitHub.""")


def print_help(prog="tk webui"):
    print(f"""{prog} (v0.2.0) — Interactive Kanban Web UI & PR review dashboard.
Created by Sampath Kumar & wedow contributors
GitHub: https://github.com/msampathkumar/ticket
License: MIT

Usage: {prog} [command|directory] [options]

Commands:
  server start [dir]       Start background web server daemon (default port: 8475)
  server stop              Stop background web server daemon
  server status            Check status of background web server daemon
  server restart [dir]     Restart background web server daemon
  start [dir]              Shortcut for 'server start'
  stop                     Shortcut for 'server stop'
  status                   Shortcut for 'server status'
  restart [dir]            Shortcut for 'server restart'
  version, --version, -v   Display version and project information
  help, --help, -h         Display this help message

Options:
  --host <host>            Host address to bind to (default: 127.0.0.1)
  --port <port>            Port number to listen on (default: 8475)
  --reload                 Enable auto-reload on code change (development mode)

Examples:
  tk webui                 # Run server in foreground on current repo
  tk webui /path/to/repo   # Run server in foreground targeting specific repo
  tk webui server start    # Start background daemon on port 8475
  tk webui server status   # Inspect running background daemon
  tk webui server stop     # Terminate background daemon
  tk webui start           # Shortcut to start background daemon

Thank you for using tk! If you find it helpful, please star the repo or contribute on GitHub.""")


def main():
    import sys
    from .server import DEFAULT_PORT, start_server, stop_server, status_server, restart_server

    if "--tk-describe" in sys.argv:
        print("tk-plugin: Interactive Kanban Web UI & PR review dashboard")
        return

    prog_name = "tk webui" if (len(sys.argv) > 0 and "tk-webui" in sys.argv[0]) else "tk webui"

    args = sys.argv[1:]
    if not args:
        # Default: run foreground server on current directory
        os.environ["INITIAL_PROJECT_DIR"] = os.path.abspath(os.getcwd())
        print(f"🚀 Starting tk-webui on http://127.0.0.1:{DEFAULT_PORT} (ASCII: T=84, K=75)")
        print(f"📁 Initial directory: {os.environ['INITIAL_PROJECT_DIR']}")
        uvicorn.run("tk_webui.main:app", host="127.0.0.1", port=DEFAULT_PORT, reload=False)
        return

    first = args[0]

    if first in ("version", "--version", "-v"):
        print_version()
        return

    if first in ("help", "--help", "-h"):
        print_help(prog_name)
        return

    # Handle 'server <action>' or shortcuts '<action>'
    if first == "server" or first in ("start", "stop", "status", "restart"):
        server_args = args[1:] if first == "server" else args
        action = server_args[0] if (first == "server" and server_args) else (first if first != "server" else "status")
        rest = server_args[1:] if first == "server" else server_args[1:]

        server_parser = argparse.ArgumentParser(prog=f"{prog_name} server", add_help=False)
        server_parser.add_argument("directory", nargs="?", default=os.getcwd(), help="Target repository directory")
        server_parser.add_argument("--host", default="127.0.0.1", help="Host address")
        server_parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number")

        if action in ("--help", "-h", "help"):
            print_help(prog_name)
            return

        parsed, extra = server_parser.parse_known_args(rest)

        if action == "start":
            sys.exit(start_server(parsed.directory, host=parsed.host, port=parsed.port))
        elif action == "stop":
            sys.exit(stop_server())
        elif action == "status":
            sys.exit(status_server())
        elif action == "restart":
            sys.exit(restart_server(parsed.directory, host=parsed.host, port=parsed.port))
        else:
            print(f"Error: unknown server action '{action}'\n\nRun '{prog_name} help' to see available commands.", file=sys.stderr)
            sys.exit(1)
        return

    # Foreground server with options or directory
    if first.startswith("-") or os.path.exists(first) or len(args) > 0:
        parser = argparse.ArgumentParser(prog=prog_name, add_help=False)
        parser.add_argument("directory", nargs="?", default=os.getcwd(), help="Initial directory to open")
        parser.add_argument("--host", default="127.0.0.1", help="Host address")
        parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Port number")
        parser.add_argument("--reload", action="store_true", help="Auto-reload on code change")
        parser.add_argument("--help", "-h", action="store_true", help="Help")
        parser.add_argument("--version", "-v", action="store_true", help="Version")

        # Check if first argument is an unrecognized command (not a flag and not a directory)
        if not first.startswith("-") and not os.path.isdir(first) and not (first.startswith("/") or first.startswith(".") or first.startswith("~")):
            print(f"Error: unknown command '{first}'\n\nRun '{prog_name} help' to see available commands.", file=sys.stderr)
            sys.exit(1)

        parsed_args = parser.parse_args(args)
        if parsed_args.help:
            print_help(prog_name)
            return
        if parsed_args.version:
            print_version()
            return

        target_dir = os.path.abspath(os.path.expanduser(parsed_args.directory))
        os.environ["INITIAL_PROJECT_DIR"] = target_dir
        print(f"🚀 Starting tk-webui on http://{parsed_args.host}:{parsed_args.port} (ASCII: T=84, K=75)")
        print(f"📁 Initial directory: {os.environ['INITIAL_PROJECT_DIR']}")
        uvicorn.run("tk_webui.main:app", host=parsed_args.host, port=parsed_args.port, reload=parsed_args.reload)
        return


if __name__ == "__main__":
    main()
