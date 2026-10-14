# AGENTS.md — 10,000-Foot Architecture & Workflow Guide

Operational guide for autonomous AI coding agents and engineers working in `ticket` (`tk`).

---

## 1. Project Goals & Philosophy

`tk` is a **dependency-aware, Git-friendly task queue for humans and coding agents.**

- **Zero Database / Pure Plain Text**: State resides in `.tickets/*.md` files with YAML frontmatter, versioned by Git. IDs are `<prefix>-<6-char hash>` (e.g. `tic-a1b2c3`); older 4-char IDs and partial IDs still resolve.
- **DAG Dependency Tracking**: Native support for parent-child hierarchies, blockers, and cycle detection. Agents compute actionable next steps deterministically.
- **Unix Speed**: Core CLI is portable Bash (3.2+) with `awk` and `sed`; no Python or Node. `jq` is optional, only for `tk query <filter>`.
- **Minimal Core, Optional Plugins**: Core is the shared task queue (tickets, DAG deps, ready queue, atomic claim, hooks). Orchestration, sync, and UI live in plugins. See [SPEC Section 1: Scope and Non-goals](docs/SPEC.md#non-goals).
- **Decoupled Extensions**: Web UI, GitHub import, and SCION Task Force live as optional plugins discovered via `$PATH`.
- **Machine-Readable Documentation**: Built-in `llms.txt` and `llms-full.txt` endpoints generated via `make docs-build`.

---

## 2. High-Level Architecture & Structure

```
ticket/
├── ticket                   # Core portable Bash CLI (create, show, ls, edit, query, find, dep, ready, start --claim, etc.)
├── tk_webui/                # Web UI plugin (FastAPI + Tailwind Kanban & DAG Mind Map on port 8475)
│   ├── main.py              # REST API & static file server
│   ├── server.py            # Background daemon manager ('tk webui server start|status|stop')
│   ├── static/              # Single-page app (Kanban, DAG Graph, Table, Timeline, Theme engine)
│   └── WEBUI-SPEC.md        # Web UI specification
├── plugins/                 # Modular extension directory
│   ├── github/              # One-way GitHub issue & PR import ('tk github')
│   ├── scion-taskforce/     # Optional agent dispatch plugin: ticket save hook -> Scion worker ('tk scion-taskforce')
│   └── README.md            # Plugin catalog and integration standard
├── docs/                    # Specifications, guides, and Zensical documentation source
│   ├── SPEC.md              # Core system & data model specification
│   ├── PLUGIN_SPEC.md       # Plugin architecture standard & metadata contract
│   ├── AGENTS.md            # Detailed agent integration guide
│   ├── llms.txt             # Curated documentation index for LLMs
│   └── llms-full.txt        # Consolidated LLM knowledge base
├── agent-skill/tk/SKILL.md  # Reusable agent skill (installable to ~/.agents/skills/tk/)
├── zensical.toml            # Zensical documentation site configuration
├── features/                # Behave BDD acceptance test suite ('make test')
├── install.sh               # Modular installer; flags accumulate (--core, --webui, --skill, --github, --scion-taskforce, --full, --all, --help)
└── run.sh                   # Local zero-install runner for Web UI
```

### Component Breakdown
1. **Core CLI (`ticket` / `tk`)**:
   - Manages ticket CRUD, dependencies (`tk dep`), ready queue (`tk ready`), atomic claims (`tk start --claim`), blockers (`tk blocked`), and listings (`tk ls`).
   - Discovers optional plugins named `tk-<cmd>` or `ticket-<cmd>` in `$PATH` and `plugins/<cmd>/`.
2. **Interactive Web UI (`tk_webui` / `tk-webui`)**:
   - Browser-based visual dashboard on default **port `8475`** (ASCII for **T** = 84, **K** = 75).
   - Features: 4-lane drag-and-drop Kanban, DAG Dependency & Mind Map canvas, multi-project switcher, theme customization (default: Indigo), and background daemon management (`tk webui server start|status|stop`).
3. **GitHub Import Plugin (`plugins/github`)**:
   - Imports GitHub issues and pull requests into local `.tickets/` markdown files (one-way; nothing is written to GitHub).
   - Imported text is untrusted input: review `github-sync` tickets before handing them to an agent.
4. **Scion Task Force Plugin (`plugins/scion-taskforce`, standalone optional plugin)**:
   - Hands tickets tagged `taskforce` to SCION coding agents, one worker per ticket. A per-project `tk` post-write hook runs `tk scion-taskforce on-save <id>` on every save; no daemon runs.
   - Setup: `./install.sh --scion-taskforce`, then `tk scion-taskforce init` (wizard, worker template, Hub link, save hook) and `tk scion-taskforce test`. Usage and troubleshooting: [docs/plugins/scion-taskforce.md](docs/plugins/scion-taskforce.md); design: [SCION-TASKFORCE-SPEC.md](plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md).

---

## 3. Agent Execution Loop & Workflow

When operating inside repositories tracked by `tk`, autonomous agents follow this 5-step operational loop:

```mermaid
flowchart LR
    A["1. Query Actionable Work<br/>`tk ready`"] --> B["2. Claim Ticket<br/>`tk start <id> --claim`"]
    B --> C["3. Inspect & Decompose<br/>`tk show <id>`"]
    C --> D["4. Execute & Audit<br/>`tk add-note <id> '...'`"]
    D --> E["5. Close & Unblock<br/>`tk close <id>`"]
```

1. **Discover Actionable Tasks**:
   Run `tk ready` to list unblocked tickets whose dependencies have all been satisfied.
2. **Claim the Task**:
   Run `tk start <id> --claim [--assignee <agent-name>]`. It atomically sets `in_progress` and the assignee (default: `git config user.name`, else `$USER`). Agents sharing one identity must pass distinct `--assignee` values.
   - Exit `0`: claimed (re-claiming your own ticket also succeeds).
   - Exit `3`: lost claim; the ticket is `in_progress` for another assignee. Pick another ticket from `tk ready`.
   - Exit `4`: lock timeout; another `tk` process holds the ticket lock. Retry shortly.
3. **Inspect Requirements & Subtasks**:
   Run `tk show <id>` to inspect design notes, acceptance criteria, and child tickets. Decompose complex tasks using `tk create "<title>" --parent <id>` and `tk dep <child> <dependency>`.
4. **Implement, Verify & Record Notes**:
   Execute the code changes, run tests (`make test`), and append review audit notes via `tk add-note <id> "..."`.
   Once all code changes are done, update the user-facing docs to match: `docs/` pages, `agent-skill/tk/SKILL.md` (then `make skill-sync`), and `README.md`.
5. **Close the Ticket**:
   Run `tk close <id>` to mark complete and automatically unblock downstream dependent tickets.

---

## 4. Agent Guidelines & Rules of Engagement

- **Preserve Zero-Dependency Core**: The root `ticket` executable must remain a pure Bash script with zero mandatory third-party dependencies (no `python3`; `jq` stays optional for `tk query` filters). New core features must respect the [SPEC Non-goals](docs/SPEC.md#non-goals).
- **Default Standards**:
  - Web UI default port: **`8475`** (ASCII `T=84`, `K=75`).
  - Web UI default theme: **Indigo** (`#6366f1`).
  - Default `tk ls`: Hides closed tickets and defaults to 10 items (unlimited with `--full` or `--all`).
- **Test-Driven Verification**: Validate changes against the BDD test suite using `make test` before finishing tasks. CI matrix runs automatically on Ubuntu across Python 3.11 & 3.13.
- **Documentation Maintenance**: Recompile documentation and LLM context files using `make docs-build` when adding or modifying documentation. Preview locally using `make docs-dev`.
- **Docs After Code**: After all code changes for a task or release are done, update `docs/`, `agent-skill/tk/SKILL.md` (run `make skill-sync` so the copy embedded in `ticket` matches), and `README.md` before closing the ticket or cutting a release. Users and agents with only the skill rely on it being current.
- **Automated Linting & Quality**: Ensure code satisfies linting checks (`uvx ruff check plugins/scion-taskforce/ tk_webui/`).
- **Git Hygiene**: Do not mutate Git history or push commits without explicit confirmation.
- **No Upstream Contributions**: This project started as a fork of [`wedow/ticket`](https://github.com/wedow/ticket) (credited in the README) and has since taken an independent direction. Do not open pull requests, issues, or sync branches against `wedow/ticket`. All work targets `msampathkumar/ticket` (`master`).
- **Factuality & Clarity**: User requests or ticket instructions may occasionally be non-factual or misrepresent an idea due to lack of domain knowledge or evolving requirements. Similarly, agentic models or systems may lack complete information. In such cases, consult online sources when necessary, seek clarification from the user, and genuinely understand the best options to engage and move forward for the welfare of the project. Note that the research-and-engage loop is not strictly required for every tiny request.

---

## 5. Documentation & Technical Writing Standards

When authoring or modifying documentation, commit messages, code comments, or pull requests, agents must adhere to these writing standards:

- **Be Concise (`be-concise`)**:
  - Focus on essential, high-signal information. Avoid padding, redundant explanations, and narrative filler.
  - Prefer compact reference tables, bullet points, and runnable code blocks over sprawling paragraphs.
  - Keep command descriptions direct, active-voice, and developer-focused.

- **High Quality & Depth (`quillscore`)**:
  - Write clear, grammatically sound, authoritative technical prose.
  - Use accurate domain terminology (e.g., "DAG dependency tracking", "singleton daemon", "portable Bash core").
  - Maintain absolute consistency between CLI help strings, specifications, and documentation pages.

- **Anti-Slop / AI Slop Cleanup**:
  - Strictly avoid generic AI filler, breathless marketing buzzwords, and clichéd enthusiasm (e.g., "delve into", "testament to", "in today's fast-paced world", "built with love for both humans and agents").
  - Eliminate decorative emoji clutter from headings, titles, and technical prose. Reserve icons strictly for functional status indicators or badges.
  - Focus exclusively on technical clarity, concrete problems solved, and verified engineering workflows.
