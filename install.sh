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

case "$MODE" in
    --core|-c)
        install_core
        ;;
    --webui|-w)
        install_webui
        ;;
    --full|-f|*)
        install_core
        install_webui
        ;;
esac

echo ""
echo "🎉 Installation complete!"
echo "Make sure $BIN_DIR is in your PATH. You can run:"
echo "   tk help           # Core CLI"
echo "   tk webui          # Launch Web UI"
