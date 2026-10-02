#!/usr/bin/env bash
set -e

BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
PLUGIN_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

if [ "${1:-}" = "--uninstall" ] || [ "${1:-}" = "-u" ]; then
    echo "🗑️  Uninstalling tk-scion-taskforce plugin from $BIN_DIR..."
    rm -f "$BIN_DIR/tk-scion-taskforce" "$BIN_DIR/ticket-scion-taskforce"
    echo "✅ tk-scion-taskforce uninstalled."
    exit 0
fi

mkdir -p "$BIN_DIR"
chmod +x "$PLUGIN_DIR/ticket-scion-taskforce"
ln -sf "$PLUGIN_DIR/ticket-scion-taskforce" "$BIN_DIR/tk-scion-taskforce"
ln -sf "$PLUGIN_DIR/ticket-scion-taskforce" "$BIN_DIR/ticket-scion-taskforce"

echo "✅ Installed standalone optional plugin to $BIN_DIR/tk-scion-taskforce"
echo "💡 Try: tk scion-taskforce help"
