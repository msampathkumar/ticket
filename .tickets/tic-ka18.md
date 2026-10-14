---
id: tic-ka18
status: closed
deps: []
links: []
created: 2026-10-14T19:42:28Z
type: bug
priority: 1
assignee: scion-agent
parent: tic-xv7i
tags: [github, security]
---
# GitHub plugin: option injection via issue/PR titles

Found during tic-x3nz. plugins/github/ticket-github passes the GitHub title to 'tk super create' as a bare positional argument. An attacker-controlled issue titled '--help' or '-p 0 ...' is parsed as tk options. Same class as tic-7hsr.

## Acceptance Criteria

- [ ] Issue titled '--help' or '-d x' imports with the title stored verbatim (or is safely prefixed) and no option is applied
- [ ] Labels and bodies also passed safely
- [ ] Behave scenario with a stubbed gh


## Notes

**2026-10-14T19:43:58Z**

Plan: tk create has no '--' and reads the title as a bare positional; option values (-d, --tags, --title) are read verbatim. Titles starting with '-' are created with a placeholder ('GitHub issue #N') then set via 'tk super update <id> --title', so they're stored verbatim and the update hook fires with the real title. Labels sanitised in jq to [letters digits _ . # + -] (commas, spaces, '/', '&', YAML brackets become '-', leading/trailing '-' stripped) since tags go into YAML flow lists and a sed replacement in update_yaml_field. Body already goes through -d (verbatim). Behave scenarios with a stub gh. Branched from origin/master before #9 merged; my diff avoids the help-string lines #9 changes.

**2026-10-14T19:47:35Z**

PR opened: https://github.com/msampathkumar/ticket/pull/14. make test: 229 scenarios passed; ruff passed. New scenarios fail on master and pass with the fix. Note: an installed ~/.local/bin/tk-github shadows the repo plugin on PATH, so the test pins the repo copy.

**2026-10-14T19:49:44Z**

Coordinator review PR #14: code approach approved; CI fails on Ubuntu in github_plugin.feature (sync exits 1 after first created ticket). Sent back for Linux fix.

**2026-10-14T19:51:56Z**

CI failure on Ubuntu: ((count++)) returns 1 when count is 0, and bash 4.1+ set -e aborts; macOS bash 3.2 does not. Pre-existing bug: on Linux sync exited after the first created/closed item. Fixed with x=$((x + 1)) (commit 9bb59ed). Verified in ubuntu:24.04 (bash 5.2, jq 1.7): feature fails with old plugin, passes with fix.

**2026-10-14T19:53:42Z**

Coordinator: reviewed and squash-merged PR #14 (after Linux fix). CI green. Placeholder-then-update for titles starting with '-', label sanitising, CR/LF collapse; also fixed pre-existing ((x++)) set -e bug that stopped sync after first item on bash>=4.1.
