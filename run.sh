#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Ensure virtual environment and tk_webui package are ready
if [ ! -x "$DIR/.venv/bin/python3" ] || ! "$DIR/.venv/bin/python3" -c "import tk_webui" &>/dev/null; then
    echo "📦 Setting up local environment for tk-webui..."
    "$DIR/install.sh" --webui
fi

# Run tk-webui directly
TARGET_DIR="${1:-$PWD}"
PORT="${PORT:-8475}"

echo "🚀 Starting tk-webui on http://127.0.0.1:$PORT for $TARGET_DIR (ASCII: T=84, K=75)"
echo "💡 Tip: To install 'tk' CLI and 'tk webui' globally to ~/.local/bin, run: ./install.sh"
echo ""

exec .venv/bin/python3 -m tk_webui.main "$TARGET_DIR" --port "$PORT"
