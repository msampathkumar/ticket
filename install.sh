#!/usr/bin/env bash
set -e

# Target directory for binaries
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

usage() {
    cat << EOF
Usage: ./install.sh [targets...]

Targets (combine freely, e.g. './install.sh --core --github'):
  --core,            -c   Core tk CLI (pure Bash, zero runtime deps)
  --webui,           -w   Web UI plugin (tk webui; Python venv via uv/pip)
  --skill,           -s   Agent skill -> ~/.agents/skills/tk/SKILL.md
  --github,          -g   Optional GitHub sync plugin (tk github)
  --scion-taskforce, -t   Optional SCION Task Force orchestrator (tk scion-taskforce)

Bundles:
  --full,            -f   Core + Web UI + Agent Skill  [default]
  --all                   Everything above, including optional plugins

Other:
  --help,            -h   Show this help

Environment:
  BIN_DIR   Install directory for executables (default: ~/.local/bin)
EOF
}

# Track what was (not) installed for the final summary
INSTALLED=()
SKIPPED_OPTIONAL=()

install_core() {
    echo "⚡ Installing core tk CLI to $BIN_DIR/tk..."
    cp -f "$DIR/ticket" "$BIN_DIR/tk"
    chmod +x "$BIN_DIR/tk"
    # Also link as 'ticket' if not conflicting
    ln -sf "$BIN_DIR/tk" "$BIN_DIR/ticket"
    echo "✅ Core CLI installed successfully!"
    INSTALLED+=("tk help              # Core CLI")
}

install_webui() {
    echo "📦 Installing tk-webui plugin..."
    if [ ! -d ".venv" ]; then
        if command -v uv &> /dev/null; then
            uv venv
            uv pip install -e .
        else
            python3 -m venv .venv
            .venv/bin/pip install -e .
        fi
    else
        if command -v uv &> /dev/null; then
            uv pip install -e .
        else
            .venv/bin/pip install -e .
        fi
    fi

    # Create tk-webui launcher with metadata
    rm -f "$BIN_DIR/tk-webui"
    cat << EOF > "$BIN_DIR/tk-webui"
#!/usr/bin/env bash
# tk-plugin: Interactive Kanban Web UI & PR review dashboard
# tk-plugin-version: 0.2.0

exec "$DIR/.venv/bin/python3" -m tk_webui.main "\$@"
EOF
    chmod +x "$BIN_DIR/tk-webui"
    echo "✅ Web UI plugin installed to $BIN_DIR/tk-webui"
    INSTALLED+=("tk webui             # Launch Web UI (port 8475)")
}

install_skill() {
    echo "🤖 Installing tk Agent Skill to $HOME/.agents/skills/tk/SKILL.md..."
    mkdir -p "$HOME/.agents/skills/tk"
    cp -f "$DIR/agent-skill/tk/SKILL.md" "$HOME/.agents/skills/tk/SKILL.md"
    echo "✅ Agent skill installed successfully!"
    INSTALLED+=("tk agent-skill       # Show installed agent skill")
}

install_github() {
    echo "🐙 Installing optional tk-github plugin to $BIN_DIR/tk-github..."
    cp -f "$DIR/plugins/github/ticket-github" "$BIN_DIR/tk-github"
    chmod +x "$BIN_DIR/tk-github"
    ln -sf "$BIN_DIR/tk-github" "$BIN_DIR/ticket-github"
    echo "✅ GitHub sync plugin installed to $BIN_DIR/tk-github"
    INSTALLED+=("tk github sync       # GitHub issue/PR sync (optional plugin)")
}

install_scion_taskforce() {
    echo "🚀 Installing optional tk-scion-taskforce plugin to $BIN_DIR/tk-scion-taskforce..."
    # The plugin owns its install/uninstall logic; delegate to keep a single source of truth.
    BIN_DIR="$BIN_DIR" bash "$DIR/plugins/scion-taskforce/install.sh"
    INSTALLED+=("tk scion-taskforce   # SCION worker orchestrator (optional plugin)")
}

# --- Argument parsing: every flag is a target; they accumulate ----------------
DO_CORE=0; DO_WEBUI=0; DO_SKILL=0; DO_GITHUB=0; DO_SCION=0

if [ $# -eq 0 ]; then
    set -- --full
fi

for arg in "$@"; do
    case "$arg" in
        --core|-c)            DO_CORE=1 ;;
        --webui|-w)           DO_WEBUI=1 ;;
        --skill|-s)           DO_SKILL=1 ;;
        --github|-g)          DO_GITHUB=1 ;;
        --scion-taskforce|-t) DO_SCION=1 ;;
        --full|-f)            DO_CORE=1; DO_WEBUI=1; DO_SKILL=1 ;;
        --all|-a)             DO_CORE=1; DO_WEBUI=1; DO_SKILL=1; DO_GITHUB=1; DO_SCION=1 ;;
        --help|-h)            usage; exit 0 ;;
        *)
            echo "❌ Unknown option: $arg" >&2
            echo "" >&2
            usage >&2
            exit 1
            ;;
    esac
done

[ "$DO_CORE" -eq 1 ]   && install_core
[ "$DO_WEBUI" -eq 1 ]  && install_webui
[ "$DO_SKILL" -eq 1 ]  && install_skill
[ "$DO_GITHUB" -eq 1 ] && install_github
[ "$DO_SCION" -eq 1 ]  && install_scion_taskforce

[ "$DO_GITHUB" -eq 0 ] && SKIPPED_OPTIONAL+=("./install.sh --github            # GitHub issue & PR sync (tk github)")
[ "$DO_SCION" -eq 0 ]  && SKIPPED_OPTIONAL+=("./install.sh --scion-taskforce   # SCION Task Force orchestrator (tk scion-taskforce)")

# --- Summary -------------------------------------------------------------------
echo ""
echo "🎉 Installation complete!"
echo "Make sure $BIN_DIR is in your PATH. You can run:"
for line in "${INSTALLED[@]}"; do
    echo "   $line"
done

if [ "${#SKIPPED_OPTIONAL[@]}" -gt 0 ]; then
    echo ""
    echo "ℹ️  Optional plugins not installed (they are discovered automatically by 'tk help' once installed):"
    for line in "${SKIPPED_OPTIONAL[@]}"; do
        echo "   $line"
    done
    echo "   ./install.sh --all               # Install everything"
fi
