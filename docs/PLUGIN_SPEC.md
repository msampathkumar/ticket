# tk - Plugin Specification Standard (PLUGIN_SPEC.md)

Architecture and compliance requirements for `tk` plugins.

---

## 1. Core Principles

1. **Decoupled**: Plugins extend `tk` without modifying the core `ticket` CLI.
2. **Optional**: Plugins are optional. Users who need only the core CLI never need external runtimes.
3. **Spec-Driven**: Every plugin maintains a `<PLUGIN-NAME>-SPEC.md` specifying commands, flags, schema, and dependencies.
4. **Isolated**: Each plugin lives in its own directory under `plugins/<plugin-name>/`.

---

## 2. Directory Layout Standard

Each plugin in the repository is organized in its own isolated subfolder:

```
plugins/
├── README.md
├── github/
│   ├── GITHUB-SPEC.md           # Plugin-specific specification
│   ├── ticket-github            # Executable binary / script
│   └── tk-github -> ticket-github
├── scion-taskforce/             # Python-backed plugin (thin bash entrypoint)
│   ├── SCION-TASKFORCE-SPEC.md
│   ├── install.sh               # Optional: standalone installer (--uninstall supported)
│   ├── scion-taskforce.yaml     # Optional: default config shipped with the plugin
│   ├── ticket-scion-taskforce   # Executable entrypoint
│   ├── tk-scion-taskforce -> ticket-scion-taskforce
│   └── tk_scion_taskforce/      # Plugin's own package; never imported by core
└── webui/
    └── WEBUI-SPEC.md -> ../../tk_webui/WEBUI-SPEC.md
```

### 2.1 Installation Contract

- The repo-level `install.sh` MUST offer a dedicated target per plugin (`--<plugin-name>`) and MUST NOT include optional plugins in the default `--full` bundle; only `--all` does.
- A plugin MAY ship its own `plugins/<name>/install.sh` (supporting `--uninstall`). If it does, the repo-level target MUST delegate to it rather than duplicating the logic.
- Installation MUST NOT touch the core `ticket` script. Discovery is purely by `$PATH`: once `tk-<name>` is installed, `tk help` lists it automatically using its `# tk-plugin:` description.

---

## 3. Metadata & Discovery Contract

`tk` automatically discovers plugins available in `$PATH` matching `tk-<command>` or `ticket-<command>`.

### 3.1 Header Comments (Scripts)
Shell, Python, or Ruby scripts MUST include metadata comments in their first 10 lines:
```bash
#!/usr/bin/env bash
# tk-plugin: Single-line description of the plugin
# tk-plugin-version: 1.0.0
```

### 3.2 Flags (Compiled Binaries)
Compiled binaries (Go, Rust, C) MUST implement:
- `--tk-describe`: Prints `tk-plugin: <description>` to stdout and exits with code 0.
- `--version` / `-v`: Prints `<plugin-name> <version>` to stdout and exits with code 0.
- `--help` / `-h`: Displays standard usage and command help.

---

## 4. Execution Protocol & Context

When `tk <plugin-command> [args...]` is executed:
1. `tk` resolves the target `.tickets/` folder.
2. `tk` sets and exports environment variables:
   - `TICKETS_DIR`: Absolute path to `.tickets/` directory.
   - `TK_SCRIPT`: Absolute path to `tk` executable.
3. `tk` invokes `tk-<plugin-command> "$@"` using `exec`.

### 4.1 Calling Core Built-Ins
Plugins can execute core `tk` routines without triggering recursion by using:
```bash
"$TK_SCRIPT" super <built-in-command> [args...]
```

---

## 5. Plugin Specification Template (`<PLUGIN-NAME>-SPEC.md`)

Each plugin's `<PLUGIN-NAME>-SPEC.md` must include:
1. **Overview & Purpose**: What the plugin does and why it exists.
2. **Commands & CLI Flags**: Exhaustive list of arguments and flags.
3. **Data Schema / Metadata**: Any tags, frontmatter keys, or file structures used.
4. **Dependencies**: External CLIs or runtimes required (e.g. `gh`, `jq`, `python3`).
5. **Installation & Uninstallation**: Instructions for installing and cleanly removing the plugin.
