# Changelog

## [Unreleased]

## [0.5.0] - 2026-10-14

### Security
- Web UI: stored XSS fixed; ticket fields are HTML-escaped and markdown is sanitised with DOMPurify (#3).
- Web UI: permissive CORS removed; a Host-header allowlist blocks DNS rebinding and cross-origin writes get 403 (#4).
- Web UI: ticket IDs passed to `tk` are validated and titles starting with `-` are rejected, so no value is parsed as a CLI option (#5).
- GitHub: imported titles starting with `-` and labels with `,` `/` `&` can no longer inject `tk` options or break the tags line (#14).
- Web UI: `tk webui server stop` checks that the recorded PID is the Web UI before signalling it (#13).
- Web UI: frontend libraries are vendored and version-pinned; no scripts load from a CDN (#11).

### Added
- Core: `tk start <id> --claim [--assignee X]` claims a ticket atomically under a per-ticket `mkdir` lock with stale-lock recovery; exit `3` on a lost claim, `4` on lock timeout (#8).
- Web UI: the board refreshes within ~3 s when tickets change on disk (#15).
- Docs: SPEC Section 1 defines core scope and non-goals (#27).
- Core: `tk dep` rejects a dependency that would create a cycle (#35).
- Core: post-write hooks. Executables in `.tickets/.hooks/post-write.d/` run after each successful write with `TK_EVENT`, `TK_TICKET_ID`, `TK_TICKET_FILE`, `TICKETS_DIR` and `TK_SCRIPT`; in the background by default (`TK_HOOKS_SYNC=1` inline, `TK_NO_HOOKS=1` off); output goes to `.tickets/.hooks/hooks.log`.
- SCION Task Force: menu-based `init` wizard with validation; runs `tk init` and `scion init` when missing.
- SCION Task Force: standard worker template `tk-worker-gemini-cli-with-api-key-auth`; `test` verifies end to end through a real ticket.
- SCION Task Force: `worker.git` (`off` default, or `branch`) and `worker.privacy` (`confidential` default, or `standard`); `status` lists what needs you and automatic actions.
- SCION Task Force: `watch` repeats `sync`; workers whose turn ended without a report are paused and noted.
- SCION Task Force: the host `tk` is mounted read-only in each worker; briefs, template and feedback tell workers to use `tk show`, `tk add-note` and `tk update`.
- SCION Task Force: `scripts/live-test.sh`, a black-box live test with real Scion workers.

### Changed
- Core: no `python3` dependency; `tk init` (projects.json) and `tk update` body rewrites are pure awk/Bash, with atomic projects.json writes (#6).
- Core: ticket IDs use a 6-char hash (`TK_ID_HASH_LENGTH`, 4-32) with a retry on local collision; 4-char IDs still resolve (#12).
- Core: `tk init` adds `.locks/` and `.hooks/hooks.log` to `.tickets/.gitignore`; the lock directory ignores itself in older repos (#19).
- Project tagline is now "Dependency-aware, Git-friendly task queue for humans and coding agents." across README, docs, SPEC, agent guides, agent skill, `package.json`, the docs site and `tk help`/`tk version`.
- Core and plugins: the scion-taskforce and Web UI help descriptions drop the "orchestrator" and "PR review" claims; the GitHub plugin is called an import.
- Web UI: layout uses the full viewport width on large screens (#18).
- Web UI: `app.js` split into ES modules under `static/js/`, no behaviour change (#26).
- Web UI: Tailwind is a prebuilt, committed stylesheet (~45 KB) instead of the in-browser Play runtime (~400 KB) (#40).
- GitHub: documented as a one-way import with an untrusted-input warning; nothing is written to GitHub (#9).
- Docs: SPEC, README, agent guides, agent skill, core CLI and Web UI pages updated for claims, IDs, scope and security model; all plugins documented as optional (#29, #30, #31, #32, #33).
- Tests: every Behave scenario runs with a sandboxed `HOME` and tk_cli state dir (#28).
- SCION Task Force: event-driven. The per-project save hook runs `on-save <id>`; `sync` catches up. Close stops the worker; removing `taskforce`, adding `no-taskforce` or deleting the ticket removes it.
- SCION Task Force: only `init` links a folder to the Scion Hub; dispatch may start Podman and re-link a configured project.
- SCION Task Force: `.scion/agents/` is excluded through `.git/info/exclude`, never `.gitignore`.
- SCION Task Force: re-running `init` keeps your values; `uninit` asks first and removes workers; `dispatch` checks dependencies.
- SCION Task Force: agent-team roles ship as skills in `.agents/skills/tk-scion-*/` (`tk scion-taskforce skills install|list`) instead of per-role Scion templates. Every ticket runs on the one worker template; a `role:<name>` tag (several allowed) makes the brief name `.agents/skills/tk-scion-<name>/SKILL.md`, and untagged tickets get a list of installed role skills. A tag naming a missing skill gets a ticket note with the install command instead of a worker. `templates install|list` remain as deprecated aliases; existing `tk-<role>` templates keep working until removed. `uninit` removes generated skills.

### Removed
- SCION Task Force: the polling daemon and `server` commands (they print a migration hint), tmux auto-accept, `test --raw`.

### Fixed
- Core: field values containing `/`, `&`, `\` or `|` are stored verbatim, newlines are rejected, only frontmatter lines are updated, and values YAML would misread are single-quoted (#16).
- Core: `tk init`/`tk create` in a folder with a non-ASCII name wrote no ticket file ("Illegal byte sequence"); the ID prefix is now ASCII, falling back to `tk` (#22).
- Core: `tk create`, `tk init` and `tk update` exit 1 with a clear error, no ID and no hook when the ticket file cannot be written (#25).
- Web UI: `server start` reports success only once the server accepts connections, with a port pre-check and the log path on failure (#7).
- Web UI: opens the directory passed to `tk webui <dir>` (`GET /api/config`) (#10).
- Web UI: projects.json writes are atomic and byte-compatible with core; unreachable projects are no longer dropped (#17).
- Web UI: notes split only on `tk add-note` timestamp lines (#20).
- Web UI: reads the `external-ref` key core writes, with the legacy `external_ref` as fallback (#21).
- Web UI: version comes from one source (0.4.0, was 0.1.0) (#23).
- Web UI: blocked/ready state matches `tk ready` / `tk blocked` (#24).
- Core: `tk dep`, `undep` and `unlink` match IDs exactly; a short ID inside a longer one (`tic-1` vs `tic-12`) no longer gives wrong results or corrupts the list (#37).
- Core: `tk agent-skill` from an installed copy printed a stale embedded skill; it now matches `agent-skill/tk/SKILL.md`, guarded by `make skill-check` and a test (#38).
- Web UI: the Tree Graph fits and centres in the viewport on open and reset (#34).
- SCION Task Force: `tk reopen` on a reviewed ticket removes `waiting-for-review` (with a note) so a new worker starts; before, the tag blocked dispatch.
- SCION Task Force: a note for a paused gemini-cli worker no longer stalls it. The worker template now ships `home/.gemini/tk-system-settings.json` (topic narration off, next-speaker check on), loaded through `GEMINI_CLI_SYSTEM_SETTINGS_PATH` so Scion's own settings stay intact. Re-run `tk scion-taskforce init` in existing projects to add it.
- SCION Task Force: a note for a paused worker resumes it first and sends the note once it runs (plus 8 s to settle). In live tests the resumed worker then acted in about 20 s instead of 2.5 min.
- SCION Task Force: `init` works in folders outside git. Scion writes `.scion` as a marker file there; the worker template now goes to Scion's project config under `~/.scion/project-configs/`.
- SCION Task Force: Scion model aliases are resolved before start, so resumed workers keep a valid model; the worker keeps existing tags when it adds the review tag.
- Docs: `make docs-build` and `make docs-dev` use `uvx zensical`, so a pyenv `zensical` shim on PATH no longer breaks them.

## [0.4.0] - 2026-10-03

### Added
- SCION Task Force: Straightforward integration wrapping the native `scion` CLI (`--project <dir>`).
- SCION Task Force: Interactive setup wizard (`tk scion-taskforce init` and `tk scion-taskforce init --defaults`) with automatic project template seeding (`.scion/templates/taskforce-worker/`).
- SCION Task Force: Verification test runner (`tk scion-taskforce test`) validating provider runtime, GCP ADC, Vertex AI Model Garden, and agent container execution.
- SCION Task Force: Automated Google Cloud Vertex AI region injection (`GOOGLE_CLOUD_REGION=us-east5`) for Anthropic Claude models on Model Garden.
- Agent Skill: Comprehensive developer and AI agent operational guide with full CLI reference, 5-step loop, and GitHub repository / documentation links.
- Interactive Web UI plugin (`tk-webui`): 4-lane Kanban board, interactive DAG dependency canvas, table view, timeline audit feed, and background daemon manager (`tk webui server start|status|stop`) on default port 8475.
- Documentation portal powered by Zensical with native Mermaid diagram support and live GitHub Pages deployment.
- Machine-readable documentation endpoints: `docs/llms.txt` index and `docs/llms-full.txt` consolidated knowledge base generated via `make docs-build`.
- NPX support: root `package.json` enabling direct agent skill installation via `npx github:msampathkumar/ticket agent-skill --install`.
- Animated terminal demo recording (`docs/images/demo.gif`) illustrating DAG unblocking and core CLI workflow.
- Standardized writing style and anti-slop guidelines in `AGENTS.md` (`be-concise`, `quillscore`, and clean technical documentation standards).

### Fixed
- SCION Task Force: Cleaned up deprecated `harness` and `harness_config` schema fields in generated agent templates.
- SCION Task Force: Enhanced Podman container discovery via suffix matching (`podman ps -q --filter name=--<id>$`).
- SCION Task Force: Automatically strip `waiting-for-review` from both main ticket and worker workspace ticket upon wake.
- Web UI: Increased border contrast depth in light theme (`border-slate-300`).
- Core: `update_yaml_field` used GNU-only `0,/re/` sed addressing; on macOS (BSD sed) adding a field that did not exist yet (e.g. `tk update <id> --tags ...` on a ticket without `tags:`) silently did nothing. Now inserts portably via awk.
- `tk github sync`: existing synced tickets now get `github-sync,pr|issue` + GitHub labels (re)applied on every sync, additively (user tags such as `taskforce` are kept); summary reports `N re-tagged`.

### Changed
- Extracted `edit`, `ls`, `query`, and `migrate-beads` commands to plugins (ticket-extras)
- `install.sh`: flags now accumulate (`./install.sh --core --github`), `--help` lists targets, unknown flags fail instead of silently defaulting to `--full`, and the summary reports which optional plugins were skipped. Optional plugin targets delegate to the plugin's own installer when one exists.

### Added
- Plugin system: executables named `tk-<cmd>` or `ticket-<cmd>` in PATH are invoked automatically
- `super` command to bypass plugins and run built-in commands directly
- `TICKETS_DIR` and `TK_SCRIPT` environment variables exported for plugins
- `help` command lists installed plugins with descriptions
- Plugin metadata: `# tk-plugin:` comment for scripts, `--tk-describe` flag for binaries
- Multi-package distribution: `ticket-core`, `ticket-extras`, and individual plugin packages
- CI scripts for publishing to Homebrew tap and AUR
- Optional `tk github` plugin (`./install.sh --github`): sync GitHub issues & PRs into `.tickets/`
- Optional `tk scion-taskforce` plugin (`./install.sh --scion-taskforce`): single global daemon that spawns a SCION worker per ticket tagged `taskforce`, verifies launch, pauses on `waiting-for-review`, detects lost/crashed pods, PR-review vs implementation worker briefs (`worker.prompt_file` override), 1 worker/project by default (hub-mode pods share the checkout), isolated-worktree support for `scion init` projects (ticket mirrored in, notes + review tag merged back), auto-accepts the Claude "trust this folder" prompt that otherwise stalls project-local pods, OpenTelemetry logs with 30-day rotation

### Plugins
- ticket-edit 1.0.0: Open ticket in $EDITOR (extracted from core)
- ticket-ls 1.0.0: List tickets with optional filters (extracted from core); `ticket-list` symlink for alias
- ticket-query 1.0.0: Output tickets as JSON, optionally filtered with jq (extracted from core)
- ticket-migrate-beads 1.0.0: Import tickets from .beads/issues.jsonl (extracted from core)

## [0.3.2] - 2026-02-03

### Fixed
- Ticket ID lookup now trims leading/trailing whitespace (fixes issue with AI agents passing extra spaces)

## [0.3.1] - 2026-01-28

### Added
- `list` command alias for `ls`
- `TICKET_PAGER` environment variable for `show` command (only when stdout is a TTY; falls back to `PAGER`)

### Changed
- Walk parent directories to find `.tickets/` directory, enabling commands from any subdirectory
- Ticket ID suffix now uses full alphanumeric (a-z0-9) instead of hex for increased entropy

### Fixed
- `dep` command now resolves partial IDs for the dependency argument
- `undep` command now resolves partial IDs and validates dependency exists
- `unlink` command now resolves partial IDs for both arguments
- `create --parent` now validates and resolves parent ticket ID
- `generate_id` now uses 3-char prefix for single-segment directory names (e.g., "plan" → "pla" instead of "p")

## [0.3.0] - 2026-01-18

### Added
- Support `TICKETS_DIR` environment variable for custom tickets directory location
- `dep cycle` command to detect dependency cycles in open tickets
- `add-note` command for appending timestamped notes to tickets
- `-a, --assignee` filter flag for `ls`, `ready`, `blocked`, and `closed` commands
- `--tags` flag for `create` command to add comma-separated tags
- `-T, --tag` filter flag for `ls`, `ready`, `blocked`, and `closed` commands

## [0.2.0] - 2026-01-04

### Added
- `--parent` flag for `create` command to set parent ticket
- `link`/`unlink` commands for symmetric ticket relationships
- `show` command displays parent title and linked tickets
- `migrate-beads` now imports parent-child and related dependencies

## [0.1.1] - 2026-01-02

### Fixed
- `edit` command no longer hangs when run in non-TTY environments

## [0.1.0] - 2026-01-02

Initial release.
