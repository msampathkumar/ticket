---
id: tic-c7wt
status: open
deps: []
links: []
created: 2026-10-01T14:18:07Z
type: feature
priority: 1
assignee: Sampath Kumar
tags: []
---
# WebUI: Add new tag in the ticket side panel

In the `tk-webui` ticket detail side panel, provide a way for users to add a new tag (e.g., `taskforce`, `no-taskforce`, `waiting-for-review`, or custom tags) and remove existing tags directly from the UI.

## Design

- Add an interactive `+ Add tag` input/chip control in the ticket detail slide-over panel in `tk_webui/static/index.html` and `tk_webui/static/app.js`.
- Wire tag additions/removals to update the ticket's `tags` array via `tk_webui/main.py` and refresh the ticket card/table view.

## Acceptance Criteria

1. Ticket detail side panel displays existing tags and an input/button to add a new tag.
2. Submitting a new tag updates the ticket frontmatter `tags` list and refreshes the UI immediately.
