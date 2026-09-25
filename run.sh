#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Ensure virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Setting up local environment for tk-webui..."
    if command -v uv &> /dev/null; then
        uv venv
        uv pip install -e .
    else
        python3 -m venv .venv
        .venv/bin/pip install -e .
    fi
fi

# Run tk-webui directly
TARGET_DIR="${1:-$PWD}"
PORT="${PORT:-8000}"

echo "🚀 Starting tk-webui on http://127.0.0.1:$PORT for $TARGET_DIR"
echo "💡 Tip: To install 'tk' CLI and 'tk webui' globally to ~/.local/bin, run: ./install.sh"
echo ""

exec .venv/bin/python3 -m tk_webui.main "$TARGET_DIR" --port "$PORT"
