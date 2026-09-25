#!/usr/bin/env bash
set -e

# Target directory for binaries
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
mkdir -p "$BIN_DIR"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

MODE="${1:---full}"

install_core() {
    echo "⚡ Installing core tk CLI to $BIN_DIR/tk..."
    cp -f "$DIR/ticket" "$BIN_DIR/tk"
    chmod +x "$BIN_DIR/tk"
    # Also link as 'ticket' if not conflicting
    ln -sf "$BIN_DIR/tk" "$BIN_DIR/ticket"
    echo "✅ Core CLI installed successfully!"
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
    cat << EOF > "$BIN_DIR/tk-webui"
#!/usr/bin/env bash
# tk-plugin: Interactive Kanban Web UI & PR review dashboard
# tk-plugin-version: 0.1.0

exec "$DIR/.venv/bin/python3" -m tk_webui.main "\$@"
EOF
    chmod +x "$BIN_DIR/tk-webui"
    echo "✅ Web UI plugin installed to $BIN_DIR/tk-webui"
}

install_skill() {
    echo "🤖 Installing tk Agent Skill to $HOME/.agents/skills/tk/SKILL.md..."
    mkdir -p "$HOME/.agents/skills/tk"
    cp -f "$DIR/skills/tk/SKILL.md" "$HOME/.agents/skills/tk/SKILL.md"
    echo "✅ Agent skill installed successfully!"
}

install_github() {
    echo "🐙 Installing tk-github plugin to $BIN_DIR/tk-github..."
    cp -f "$DIR/plugins/github/ticket-github" "$BIN_DIR/tk-github"
    chmod +x "$BIN_DIR/tk-github"
    ln -sf "$BIN_DIR/tk-github" "$BIN_DIR/ticket-github"
    echo "✅ GitHub sync plugin installed to $BIN_DIR/tk-github"
}

case "$MODE" in
    --core|-c)
        install_core
        ;;
    --webui|-w)
        install_webui
        ;;
    --skill|-s)
        install_skill
        ;;
    --github|-g)
        install_github
        ;;
    --all)
        install_core
        install_webui
        install_skill
        install_github
        ;;
    --full|-f|*)
        install_core
        install_webui
        install_skill
        ;;
esac

echo ""
echo "🎉 Installation complete!"
echo "Make sure $BIN_DIR is in your PATH. You can run:"
echo "   tk help           # Core CLI"
echo "   tk webui          # Launch Web UI"
