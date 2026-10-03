# Changelog

## [Unreleased]

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
