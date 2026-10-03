#!/bin/bash
set -euo pipefail

# This script concatenates all documentation, specifications, and architecture files
# into a single consolidated file for LLM and AI agent consumption.
# Adapted from A2A protocol scripts for ticket (tk).

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

OUTPUT_FILE="docs/llms-full.txt"
DOCS_DIR="docs"
PROJECT_NAME="ticket (tk) — Minimal, dependency-aware task tracker. Built to scale agentic workflows."

echo "--- Generating consolidated LLM context file: ${OUTPUT_FILE} ---"

# Clear output file and write header
cat <<EOF >"${OUTPUT_FILE}"
# ${PROJECT_NAME} — Full Documentation & Knowledge Base

This file is a consolidated, single-file compilation of all documentation, specifications,
guides, and architecture references for the ticket (tk) project, optimized for LLM and AI coding agent consumption.

Layout-only markup (styling wrappers and HTML comments) is stripped from the Markdown sources,
leaving clean, semantic Markdown formatted in <file path="..."> tags.

EOF

# Include llms.txt as curated index
if [ -f "${DOCS_DIR}/llms.txt" ]; then
  echo "Including index from ${DOCS_DIR}/llms.txt"
  {
    echo "## Documentation Index & Overview"
    echo
    cat "${DOCS_DIR}/llms.txt"
    echo
    echo "---"
    echo
  } >>"${OUTPUT_FILE}"
fi

# Helper function to drop layout-only HTML markup while preserving code blocks and prose
strip_layout_markup() {
  awk '
    /^[[:space:]]*(```|~~~)/ { in_fence = !in_fence; print; next }
    in_fence { print; next }
    /^[[:space:]]*<\/?(div|span|section)[^>]*>[[:space:]]*$/ { next }
    /^[[:space:]]*<!--([^-]|-[^-])*-->[[:space:]]*$/ { next }
    { print }
  ' "$1"
}

# Helper function to append file content with XML-style tags
append_file() {
  local file_path="$1"
  local display_path="${2:-$file_path}"
  if [ -f "$file_path" ]; then
    echo "Appending: $file_path"
    {
      echo "<file path=\"${display_path}\">"
      if [[ "$file_path" == *.md ]]; then
        strip_layout_markup "$file_path"
      else
        cat "$file_path"
      fi
      echo "</file>"
      echo
    } >>"${OUTPUT_FILE}"
  else
    echo "Warning: File not found, skipping: $file_path" >&2
  fi
}

# Build file list
FILES_TO_INCLUDE=()

# Root critical files
[ -f "README.md" ] && FILES_TO_INCLUDE+=("README.md")
[ -f "AGENTS.md" ] && FILES_TO_INCLUDE+=("AGENTS.md")
[ -f "CHANGELOG.md" ] && FILES_TO_INCLUDE+=("CHANGELOG.md")
[ -f "agent-skill/tk/SKILL.md" ] && FILES_TO_INCLUDE+=("agent-skill/tk/SKILL.md")

# Plugin specifications
[ -f "tk_webui/WEBUI-SPEC.md" ] && FILES_TO_INCLUDE+=("tk_webui/WEBUI-SPEC.md")
[ -f "plugins/github/GITHUB-SPEC.md" ] && FILES_TO_INCLUDE+=("plugins/github/GITHUB-SPEC.md")
[ -f "plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md" ] && FILES_TO_INCLUDE+=("plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md")

# Core documentation files
while IFS= read -r doc_file; do
  FILES_TO_INCLUDE+=("$doc_file")
done < <(find "${DOCS_DIR}" -type f -name "*.md" \
  -not -path "docs/llms.txt" \
  -not -path "docs/llms-full.txt" | sort)

# Write file index manifest
echo "## Consolidated File Index" >>"${OUTPUT_FILE}"
echo >>"${OUTPUT_FILE}"
for f in "${FILES_TO_INCLUDE[@]}"; do
  echo "- ${f}" >>"${OUTPUT_FILE}"
done

{
  echo
  echo "---"
  echo
} >>"${OUTPUT_FILE}"

# Append file contents
for f in "${FILES_TO_INCLUDE[@]}"; do
  append_file "$f" "$f"
done

echo "✅ Consolidated LLM file generated successfully at ${OUTPUT_FILE} ($(wc -l < "${OUTPUT_FILE}") lines, $(wc -c < "${OUTPUT_FILE}") bytes)"
