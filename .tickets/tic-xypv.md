---
id: tic-xypv
status: closed
deps: []
links: []
created: 2026-10-14T19:40:25Z
type: bug
priority: 2
assignee: scion-agent
parent: tic-4294
tags: [core]
---
# Core: escape sed metacharacters in YAML field updates

Follow-up noted in PR #5 and PR #8. update_yaml_field uses sed replacement; values containing '/', '&', '\\' or newlines (assignee, external_ref, claim assignee) corrupt or break the update.

## Acceptance Criteria

- [ ] tk update -a 'a/b & c' and tk start --claim --assignee 'a/b' store the value verbatim
- [ ] Newlines rejected or escaped
- [ ] Behave scenario


## Notes

**2026-10-14T19:48:44Z**

Plan/decisions: update_yaml_field rewritten as one awk pass (value via ENVIRON -> '/', '&', '\', '|' verbatim), limited to frontmatter (old sed also rewrote matching body lines). Newlines/CR rejected with 'Error: <field> must be a single line' (update, claim, create). Scalars that plain YAML would misread (leading indicator chars, ': ', ' #', trailing ':', edge spaces) are single-quoted; yaml_field unquotes, so claim compares raw values. Plain values unchanged (backward compatible). New fields now insert at end of frontmatter.

**2026-10-14T19:51:49Z**

PR opened: https://github.com/msampathkumar/ticket/pull/16. make test 232/232 (236/236 merged with current master), shellcheck clean, ruff clean. yaml.safe_load round-trip OK for 26 sample values.

**2026-10-14T19:53:57Z**

Coordinator: reviewed and squash-merged PR #16. CI green. awk/ENVIRON update_yaml_field (frontmatter only), _yaml_scalar minimal quoting, single-line validation.
