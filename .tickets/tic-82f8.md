---
id: tic-82f8
status: closed
deps: []
links: []
created: 2026-10-04T21:52:33Z
type: feature
priority: 2
assignee: scion-agent
tags: [scion-taskforce, skills, design]
---
# scion-taskforce: replace per-role Scion templates with skills on one worker template

Today `templates install` builds one Scion template per agent-team role (`.scion/templates/tk-<role>/`: agents.md with the tk contract, system-prompt.md, vendored skills/). A `role:<name>` tag picks the template.

Proposal: keep ONE worker template for the pod (harness, auth, image, tk mount) and ship role knowledge as skills installed in the project's `.agents/skills/` at init. Template = how the pod runs; skill = how to do the job.

Why:
- One template to maintain instead of ~8 near-duplicates.
- One worker can combine several skills (e.g. code-review + security-audit).
- The same skills work for humans and local agents outside Scion.
- Fits the plugin scope: a simple ticket <-> Scion bridge.

## Design

Decisions (agreed 2026-10-04):
1. Location: project `.agents/skills/`. Every generated skill uses the prefix `tk-scion-` (`.agents/skills/tk-scion-code-reviewer/SKILL.md`) so it never collides with other skills. Referenced upstream skills get the same prefix; the SKILL.md `name:` matches the folder name.
2. Selection: a `role:<name>` tag maps to skill `tk-scion-<name>`; several role tags are allowed. Untagged tickets fall back to choosing by description (understood to be less reliable).
3. The brief carries everything at assignment time; no reliance on harness skill discovery:
   - the ticket details (as today);
   - "use `tk` for reading updates and reporting" (as today);
   - tagged: "Read and follow `.agents/skills/tk-scion-<name>/SKILL.md` before starting" (mandatory, by path);
   - untagged: a short list of installed `tk-scion-*` skills (name + description) with "use one only if it clearly fits".
   Because the brief names the file path, the design works for any harness (claude/opencode/codex need no separate check).
4. Persona: fold upstream system-prompt.md into the skill body. Per-role model/resource settings are dropped.

Sketch:
- `tk scion-taskforce skills install [role...] [--force]` replaces `templates install`: vendors agent-team role guidance + referenced skills at the pinned UPSTREAM_REF into `.agents/skills/tk-scion-*/`, keeps UPSTREAM.md + LICENSE (marker for generated skills), keeps the privacy filter (PUBLISHING_SKILLS dropped when confidential).
- Each role skill starts with the tk contract (use tk show/add-note/update, never close tickets).
- `role_template_for()` goes away: every ticket runs on the one worker template.
- `templates install` stays as a deprecated alias (`# deprecated: ..., remove after 2027-04-01`). `uninit` removes generated `tk-scion-*` skills (marker only) and the old generated tk-<role> templates.
- Init wizard step 8 becomes "agent-team skills".
- Git (default, to confirm): generated skills are local; they are not committed or ignored automatically, and init prints how to do either.

## Acceptance Criteria

- One worker template per project; no new tk-<role> templates are generated.
- `skills install` writes the default roles to `.agents/skills/tk-scion-<role>/`, all names prefixed; re-run is idempotent; --force refreshes generated skills only and never touches other skills.
- A ticket tagged `role:<name>` gets a brief that names `.agents/skills/tk-scion-<name>/SKILL.md` and the tk reporting rules; an untagged ticket gets the skill list.
- A tag naming a missing skill is reported in a ticket note (with the install command) instead of starting a worker silently without it.
- A live gemini-cli worker reads the named skill and reports via tk (verified in a pod).
- Confidential privacy drops publishing skills.
- Existing tk-<role> templates keep working until removed; docs explain the migration.
- BDD scenarios cover install, prefixing, privacy filter, brief skill line (tagged and untagged), missing skill, uninit cleanup; make test, ruff, docs build pass.


## Notes

**2026-10-04T22:23:29Z**

Implemented: skills replace per-role templates.
- skills install [role...] [--force] [--from] [--ref] writes .agents/skills/tk-scion-<role>/ (tk contract + persona + agents.md + related skill paths) and tk-scion-<skill>/ (name: rewritten); UPSTREAM.md marks generated folders. templates install|list = deprecated alias (remove after 2027-04-01).
- One worker template for all tickets. Brief: role tags -> mandatory SKILL.md path(s); untagged -> list of role skills + hand-made tk-scion-* skills; {skills} placeholder for prompt_file.
- Missing role skill: note with install command, no worker, queue continues. Old tk-<role> templates still used for roles without a skill.
- uninit removes generated tk-scion-* skills; branch-mode worktrees get the skills copied in. Git: not committed or ignored; install prints both options.
- Wizard step 8 = agent-team skills. Docs, spec, help updated.
Verified: make test 212/212, ruff clean, docs build OK (zensical via uvx; make docs-build fails locally on a pyenv shim). Real upstream install of 8 default roles OK. Live gemini-cli worker (vertex-ai) in /tmp read .agents/skills/tk-scion-developer/SKILL.md, quoted its heading, reported via tk add-note and added waiting-for-review; cleaned up.
Found (not fixed): scion v0.2.21 writes a .scion marker FILE in non-git folders, so init fails there (NotADirectoryError seeding .scion/templates).

**2026-10-04T23:03:42Z**

Follow-up (user request): removed the commented-out template code and unused helpers (USER.md: delete, do not keep deprecated code). Dropped the worktree skill copy per USER.md 'simple bridge, no worktree handling' (coder-soul: recorded preferences + YAGNI); docs now say a worker's own worktree sees skills only when committed. templates alias and old tk-<role> template fallback kept (contracts).
