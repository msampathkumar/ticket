#!/usr/bin/env bash
# Smoke-test the release assets in dist/ (run `make dist` first, or `make dist-check`):
# verify SHA256SUMS, install tk from tk-core.zip into a clean temp dir outside the repo,
# then run tk version/init/create/ready using only that file.
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${DIST_DIR:-$ROOT_DIR/dist}"

if command -v sha256sum >/dev/null 2>&1; then
    sha256_check() { sha256sum -c "$@"; }
else
    sha256_check() { shasum -a 256 -c "$@"; }
fi

(cd "$DIST_DIR" && sha256_check SHA256SUMS)

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

unzip -q "$DIST_DIR/tk-core.zip" -d "$tmp/zip"
for f in ticket LICENSE INSTALL.md; do
    [ -f "$tmp/zip/$f" ] || { echo "Error: tk-core.zip is missing $f" >&2; exit 1; }
done
cmp -s "$tmp/zip/ticket" "$DIST_DIR/tk" || { echo "Error: dist/tk differs from ticket in tk-core.zip" >&2; exit 1; }

mkdir -p "$tmp/bin" "$tmp/project"
cp "$tmp/zip/ticket" "$tmp/bin/tk"
chmod +x "$tmp/bin/tk"

cd "$tmp/project"
unset TICKETS_DIR
tk="$tmp/bin/tk"
"$tk" version | head -n 1
"$tk" init >/dev/null
id="$("$tk" create "Smoke test ticket")"
"$tk" ready | grep -q "$id" || { echo "Error: $id not listed by tk ready" >&2; exit 1; }
echo "dist check OK: installed from tk-core.zip, created $id"
