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

find_python_interpreter() {
    # 1. Explicit PYTHON environment variable override
    if [ -n "${PYTHON:-}" ] && [ -x "$PYTHON" ]; then
        if "$PYTHON" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            echo "$PYTHON"
            return 0
        fi
    fi

    # 2. Pyenv active python (if pyenv is installed and managing Python)
    if command -v pyenv &>/dev/null; then
        local pyenv_py
        pyenv_py="$(pyenv which python3 2>/dev/null || true)"
        if [ -n "$pyenv_py" ] && [ -x "$pyenv_py" ]; then
            if "$pyenv_py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
                echo "$pyenv_py"
                return 0
            fi
        fi
    fi

    # 3. Standard python3 in PATH
    if command -v python3 &>/dev/null; then
        local p3
        p3="$(command -v python3)"
        if "$p3" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            echo "$p3"
            return 0
        fi
    fi

    # 4. Common macOS (Homebrew / Xcode Command Line Tools) and Linux standard paths
    local candidates=(
        "/opt/homebrew/bin/python3"
        "/usr/local/bin/python3"
        "/usr/bin/python3"
        "$HOME/.pyenv/shims/python3"
    )
    for candidate in "${candidates[@]}"; do
        if [ -x "$candidate" ]; then
            if "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
                echo "$candidate"
                return 0
            fi
        fi
    done

    # 5. Fallback: python in PATH (if symlinked to python3 >= 3.9)
    if command -v python &>/dev/null; then
        local p
        p="$(command -v python)"
        if "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            echo "$p"
            return 0
        fi
    fi

    return 1
}

install_webui() {
    echo "📦 Installing tk-webui plugin..."

    local python_bin
    if ! python_bin="$(find_python_interpreter)"; then
        local detected=""
        if command -v python3 &>/dev/null; then
            detected="$(python3 --version 2>&1 || true)"
        fi
        echo "❌ No suitable Python 3 (>= 3.9) found." >&2
        if [ -n "$detected" ]; then
            echo "   Detected: $detected, but tk-webui requires Python >= 3.9" >&2
        fi
        echo "💡 Installation options:" >&2
        echo "   • macOS: brew install python  (or 'xcode-select --install')" >&2
        echo "   • Linux: sudo apt install python3 python3-venv python3-pip" >&2
        echo "   • Pyenv: pyenv install 3.12 && pyenv global 3.12" >&2
        return 1
    fi

    # Validate existing .venv health; rebuild if broken or pointing to missing interpreter
    if [ -d "$DIR/.venv" ]; then
        if [ ! -x "$DIR/.venv/bin/python3" ] || ! "$DIR/.venv/bin/python3" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
            echo "⚠️  Existing .venv is broken or uses a missing Python interpreter. Rebuilding..."
            rm -rf "$DIR/.venv"
        fi
    fi

    if command -v uv &> /dev/null && uv --version &> /dev/null; then
        echo "⚡ Using uv for environment setup..."
        if [ ! -d "$DIR/.venv" ]; then
            uv venv "$DIR/.venv" --python "$python_bin" || uv venv "$DIR/.venv"
        fi
        VIRTUAL_ENV="$DIR/.venv" uv pip install -e "$DIR"
    else
        echo "🐍 Using Python: $python_bin ($("$python_bin" --version 2>&1))"
        if [ ! -d "$DIR/.venv" ]; then
            echo "🔨 Creating virtual environment at $DIR/.venv..."
            unset PYTHONHOME
            if ! "$python_bin" -m venv "$DIR/.venv"; then
                echo "❌ Failed to create virtual environment with $python_bin." >&2
                echo "💡 On Debian/Ubuntu: sudo apt install python3-venv python3-pip" >&2
                echo "💡 On macOS: xcode-select --install" >&2
                return 1
            fi
        fi

        # Ensure pip is present inside the virtual environment
        if ! "$DIR/.venv/bin/python3" -m pip --version &>/dev/null; then
            echo "🔧 Bootstrapping pip inside .venv..."
            "$DIR/.venv/bin/python3" -m ensurepip --upgrade 2>/dev/null || \
            "$DIR/.venv/bin/python3" -m ensurepip --default-pip 2>/dev/null || true
        fi

        if ! "$DIR/.venv/bin/python3" -m pip --version &>/dev/null; then
            echo "❌ 'pip' is not available in $DIR/.venv." >&2
            echo "💡 Please ensure 'ensurepip' or 'python3-pip' is available." >&2
            return 1
        fi

        echo "📥 Installing tk-webui dependencies into .venv..."
        unset PYTHONHOME
        VIRTUAL_ENV="$DIR/.venv" "$DIR/.venv/bin/python3" -m pip install -e "$DIR"
    fi

    # Verify installation
    if ! "$DIR/.venv/bin/python3" -c "import tk_webui" &>/dev/null; then
        echo "❌ Verification failed: tk_webui could not be imported from $DIR/.venv." >&2
        return 1
    fi

    # Ensure plugin script exists and has executable permissions
    mkdir -p "$DIR/plugins/webui"
    chmod +x "$DIR/plugins/webui/ticket-webui"
    ln -sf "ticket-webui" "$DIR/plugins/webui/tk-webui"

    # Link launcher into BIN_DIR
    rm -f "$BIN_DIR/tk-webui" "$BIN_DIR/ticket-webui"
    ln -sf "$DIR/plugins/webui/ticket-webui" "$BIN_DIR/tk-webui"
    ln -sf "$BIN_DIR/tk-webui" "$BIN_DIR/ticket-webui"

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
