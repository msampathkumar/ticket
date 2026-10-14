#!/usr/bin/env bash
# Rebuild tk_webui/static/css/tailwind.css with the pinned Tailwind standalone CLI.
# Maintainer-only: the CSS is committed, so installing or running tk needs neither this script nor Node.
# Usage: scripts/build-webui-css.sh
set -euo pipefail

VERSION="3.4.17"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/tk/tailwindcss-$VERSION"

case "$(uname -s)-$(uname -m)" in
    Darwin-arm64)  asset="tailwindcss-macos-arm64";  sha="a1d0c7985759accca0bf12e51ac1dcbf0f6cf2fffb62e6e0f62d091c477a10a3" ;;
    Darwin-x86_64) asset="tailwindcss-macos-x64";    sha="6cbdad74be776c087ffa5e9a057512c54898f9fe8828d3362212dfe32fc933a3" ;;
    Linux-x86_64)  asset="tailwindcss-linux-x64";    sha="7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4" ;;
    Linux-aarch64|Linux-arm64) asset="tailwindcss-linux-arm64"; sha="69b1378b8133192d7d2feb12a116fa12d035594f58db3eff215879e4ad8cf39b" ;;
    *) echo "Unsupported platform: $(uname -s)-$(uname -m)" >&2; exit 1 ;;
esac

bin="$CACHE/$asset"
if [[ ! -x "$bin" ]]; then
    mkdir -p "$CACHE"
    curl -fsSL -o "$bin.tmp" "https://github.com/tailwindlabs/tailwindcss/releases/download/v$VERSION/$asset"
    actual=$( (command -v sha256sum >/dev/null && sha256sum "$bin.tmp" || shasum -a 256 "$bin.tmp") | awk '{print $1}')
    if [[ "$actual" != "$sha" ]]; then
        rm -f "$bin.tmp"
        echo "Checksum mismatch for $asset: got $actual, want $sha" >&2
        exit 1
    fi
    chmod +x "$bin.tmp"
    mv "$bin.tmp" "$bin"
fi

cd "$ROOT/tk_webui"
"$bin" -c tailwind.config.js -i tailwind.input.css -o static/css/tailwind.css
