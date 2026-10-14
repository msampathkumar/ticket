#!/usr/bin/env bash
# Build downloadable tk core release assets into dist/:
#   dist/tk           the `ticket` script (mode 755)
#   dist/tk-core.zip  ticket, LICENSE, INSTALL.md
#   dist/SHA256SUMS   checksums for tk and tk-core.zip
#
# Asset names carry no version, so releases/latest/download/<name> stays stable.
# Output is deterministic: fixed mtimes and modes, fixed entry order, no extra zip fields.
#
# Usage: scripts/build-dist.sh [ref]   # git ref to take ticket and LICENSE from (default: HEAD)
#        DIST_DIR=out scripts/build-dist.sh v0.5.0
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REF="${1:-HEAD}"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"
REPO_URL="https://github.com/msampathkumar/ticket"

command -v zip >/dev/null 2>&1 || { echo "Error: zip is required" >&2; exit 1; }

if command -v sha256sum >/dev/null 2>&1; then
    sha256() { sha256sum "$@"; }
elif command -v shasum >/dev/null 2>&1; then
    sha256() { shasum -a 256 "$@"; }
else
    echo "Error: sha256sum or shasum is required" >&2
    exit 1
fi

git -C "$ROOT_DIR" rev-parse --verify --quiet "$REF^{commit}" >/dev/null \
    || { echo "Error: unknown git ref '$REF'" >&2; exit 1; }

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

git -C "$ROOT_DIR" show "$REF:ticket" > "$stage/ticket"
git -C "$ROOT_DIR" show "$REF:LICENSE" > "$stage/LICENSE"

cat > "$stage/INSTALL.md" <<EOF
# Install tk (core CLI)

\`ticket\` is a single portable Bash script. No build step, no Python or Node.

## Requirements

- Bash 3.2+ and standard Unix tools (awk, sed, grep, find) on macOS or Linux
- Optional: \`jq\` for \`tk query <filter>\`, \`rg\` for faster \`tk find\`

## Install

\`\`\`bash
unzip tk-core.zip -d tk-core
mkdir -p ~/.local/bin
cp tk-core/ticket ~/.local/bin/tk
chmod +x ~/.local/bin/tk
\`\`\`

Make sure \`~/.local/bin\` is on your PATH, e.g. add this to ~/.bashrc or ~/.zshrc:

\`\`\`bash
export PATH="\$HOME/.local/bin:\$PATH"
\`\`\`

## Verify

\`\`\`bash
tk version
\`\`\`

Checksums for each release are in SHA256SUMS on the release page:
$REPO_URL/releases/latest

Full documentation: https://msampathkumar.github.io/ticket/
EOF

chmod 755 "$stage/ticket"
chmod 644 "$stage/LICENSE" "$stage/INSTALL.md"
# Fixed timestamp (zip stores local time, so pin TZ for both touch and zip).
export TZ=UTC
touch -t 198001010000 "$stage/ticket" "$stage/LICENSE" "$stage/INSTALL.md"

mkdir -p "$DIST_DIR"
rm -f "$DIST_DIR/tk" "$DIST_DIR/tk-core.zip" "$DIST_DIR/SHA256SUMS"

(cd "$stage" && zip -q -X -D "$DIST_DIR/tk-core.zip" INSTALL.md LICENSE ticket)
cp -p "$stage/ticket" "$DIST_DIR/tk"
(cd "$DIST_DIR" && sha256 tk tk-core.zip > SHA256SUMS)

echo "Built from $REF:"
(cd "$DIST_DIR" && cat SHA256SUMS)
