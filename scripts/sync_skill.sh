#!/usr/bin/env bash
# Keep the fallback skill embedded in `ticket` (_skill_content heredoc) identical to
# agent-skill/tk/SKILL.md. Installed copies of tk (e.g. ~/.local/bin/tk) have no SKILL.md
# next to them, so `tk agent-skill [--install]` prints this embedded copy.
#
# Usage: scripts/sync_skill.sh          # rewrite the heredoc from SKILL.md
#        scripts/sync_skill.sh --check  # exit 1 if they differ (no changes)
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TICKET="$ROOT_DIR/ticket"
SKILL="$ROOT_DIR/agent-skill/tk/SKILL.md"
DELIM="TK_SKILL_EOF"

if grep -qx "$DELIM" "$SKILL"; then
    echo "Error: $SKILL contains a line '$DELIM' (the heredoc delimiter)" >&2
    exit 1
fi

tmp="$(mktemp)"
trap 'rm -f "$tmp"' EXIT

# Replace the body of the heredoc that starts inside _skill_content().
awk -v skill="$SKILL" -v delim="$DELIM" '
    state == 0 && /^_skill_content\(\) \{/ { state = 1 }
    state == 1 && $0 == "    cat << '\''" delim "'\''" {
        print
        while ((getline line < skill) > 0) print line
        state = 2
        next
    }
    state == 2 && $0 == delim { state = 3; print; next }
    state == 2 { next }
    { print }
    END { if (state != 3) { print "sync_skill: heredoc not found in ticket" > "/dev/stderr"; exit 2 } }
' "$TICKET" > "$tmp"

if [[ "${1:-}" == "--check" ]]; then
    if cmp -s "$tmp" "$TICKET"; then
        echo "Embedded skill in ticket matches agent-skill/tk/SKILL.md"
    else
        echo "Embedded skill in ticket is out of date; run: make skill-sync" >&2
        exit 1
    fi
else
    cat "$tmp" > "$TICKET"   # keep the file mode of ticket
    echo "Synced embedded skill in ticket from agent-skill/tk/SKILL.md"
fi
