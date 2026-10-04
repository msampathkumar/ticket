---
title: SCION Task Force
description: Hand tk tickets to SCION coding agents through a save hook, then review and close.
---

Hand a ticket to an AI coding agent: tag it `taskforce`, and saving it starts a [SCION](https://github.com/GoogleCloudPlatform/scion) worker. You review the worker's report on the ticket, then close the ticket, which stops the worker. Ticket in, report out: the ticket is the only interface, and the project does not need to be a git repository.

The plugin (`tk-scion-taskforce`) runs only when a ticket is saved. No daemon runs. For the narrative walkthrough, see the [SCION Task Force Workflow](../workflows/scion-taskforce.md). For design and internals, see [SCION-TASKFORCE-SPEC.md](https://github.com/msampathkumar/ticket/blob/main/plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md).

## Prerequisites

| Requirement | Check |
| :--- | :--- |
| `scion` CLI on `$PATH` | `scion --version` |
| Podman or Docker, running | `podman ps` |
| Python 3.9+ (PyYAML optional) | `python3 --version` |
| Model credentials for the harness | `gemini-cli`: `GEMINI_API_KEY` stored as a Scion Hub secret (`scion hub secret list --scope=hub`). Other harnesses: Vertex AI with `gcloud auth application-default login` |

## Install

```bash
./install.sh --scion-taskforce
```

This links `tk-scion-taskforce` into `~/.local/bin/`. Keep that directory on your `$PATH`.

## Quick start

```bash
tk scion-taskforce init                            # setup wizard; offers to run `test` at the end
tk scion-taskforce test                            # end-to-end check through a real ticket
tk create "Fix the login redirect" --tags taskforce # the save starts a worker
tk show <id>                                       # read the worker's report
tk add-note <id> "Also cover the logout path"      # forwarded to the worker
tk close <id>                                      # stops the worker
```

## Setup wizard

`tk scion-taskforce init` runs `tk init` when `.tickets/` is missing and `scion init` when `.scion/` is missing. In a terminal it then asks eight questions. Each is a numbered menu: Enter takes the default (`*`), `Other` takes typed input, and `q` quits without changes. You confirm a summary before anything is written.

| # | Question | Options | Validation |
| :--- | :--- | :--- | :--- |
| 1 | Harness | From `scion harness-config list`. Default `gemini-cli`, else Scion's `default_harness_config` | Must be installed |
| 2 | Model | The harness's aliases (`small`, `medium`, `large`) or its default. `opencode` also lists `google-vertex/` Gemini IDs | No quotes or backslashes |
| 3 | Google Cloud project | Detected from `GOOGLE_CLOUD_PROJECT` or `gcloud`. Skipped for `gemini-cli` | Project ID format |
| 4 | Vertex AI location | `europe-west3` (default), `global`, `eu`, `europe-west4`, `us-central1`, `us-east5`. Skipped for `gemini-cli` | Google Cloud location; AWS-style names are rejected |
| 5 | Opt-in tag | `taskforce` | Letters, digits, `-_.` |
| 6 | Max concurrent workers per project | 1 (recommended), 2, 3 | 1–10 |
| 7 | Privacy | `confidential` (recommended), `standard` | Menu only |
| 8 | Role templates | `recommended` (default set), `none`, or a comma list | Role names |

Auth follows the harness:

| Harness | `extra_start_args` | Credentials |
| :--- | :--- | :--- |
| `gemini-cli` | `--harness-auth api-key` | `GEMINI_API_KEY` Hub secret |
| any other | `--harness-auth vertex-ai` | ADC; `provider.gcp_project` and `provider.gcp_region` are passed as `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_REGION`, overriding the shell |

`init` writes or changes these files:

| Path | Purpose |
| :--- | :--- |
| `.scion-taskforce/scion-taskforce.yaml` | Project config with every key commented |
| `.scion/templates/tk-worker-gemini-cli-with-api-key-auth/` | Worker template: `scion-agent.yaml`, `agents.md`, `system-prompt.md` |
| `.agents/skills/tk-scion-*/` | Agent-team role skills, if chosen (see [Role skills](#role-skills)) |
| `.tickets/.hooks/post-write.d/scion-taskforce` | The save hook |
| `.tickets/.hooks/.gitignore`, `.tickets/.gitignore` | Ignore the hook log, the hook and the log symlink |

`init` also links the folder to the Scion Hub once (`scion hub link`). Dispatch links only a project that has a task force config and became unlinked. Re-running `init` keeps your config values and template edits. `--defaults` skips the questions and installs no role skills; `--force` starts over.

## Lifecycle

Every successful ticket write (CLI or Web UI) runs `tk scion-taskforce on-save <id>` in the background. It acts only on tickets carrying the opt-in tag:

| When a tagged ticket… | The task force… |
| :--- | :--- |
| is open, its deps are closed, and a slot is free | Notes "request noted", starts a worker, verifies it runs, then sets `in_progress` |
| is ready, but all slots are busy | Notes "queued (N of M workers busy)"; starts it when a slot frees |
| has open deps | Notes "waiting on dependencies"; starts it when the blocker closes |
| gets a human note while its worker is active | Forwards the note to the worker, waking it if paused |
| gets `waiting-for-review` from its worker | Pauses the worker and starts the next queued ticket |
| is closed | Stops the worker and starts the next queued ticket |
| loses the `taskforce` tag or gains `no-taskforce` | Stops and deletes the worker and notes it (a worker branch, if any, is kept) |
| is deleted (seen on the next save or `sync`) | Stops and deletes the worker |

`tk scion-taskforce gc` deletes the stopped workers of tickets closed more than `watcher.gc_retention_days` (5) days ago.

Status notes start with `**Task Force:**`. They are written straight to the file, so they never re-trigger the hook and are never forwarded.

Writes that bypass `tk` fire no hook: hand edits, `git pull` and worker edits. A worker's report therefore lands on the next save of any ticket in the project, or when you run `tk scion-taskforce sync`. `sync` also checks each running pod:

- A dead pod gets a "worker lost" note.
- A pod whose Scion activity is `completed`, `waiting_for_input` or `limits_exceeded` has finished its turn. Its report is merged; without one, the worker is paused with a note, which frees its slot. Add a note to answer or redirect it.

To pick up reports without saving anything, keep `tk scion-taskforce watch` running in a terminal. It repeats `sync` every 60 seconds until you press Ctrl-C. Nothing runs in the background after that.

## Git, privacy and role skills

### Git is optional

`worker.git` sets what workers may do with git:

| Value | Worker behaviour |
| :--- | :--- |
| `off` (default) | No `git init`, `commit`, `checkout`, `stash` or `push`. Changes stay in the working tree and the report lists every changed file. PR reviews read `gh pr diff` without checking out. Works in plain folders |
| `branch` | Commits on the ticket branch (`scion start --branch <id>`), never pushes. Git repos only |

### Privacy

`worker.privacy` defaults to `confidential`. Workers are then told not to upload or publish project content, push, or comment on external systems. `skills install` drops skills that publish content, and `status` warns when the Scion Hub endpoint is not local. Set `standard` to lift these limits, for example to let PR reviews post a `gh pr comment`.

### Role skills

Every worker runs on the project's one worker template (how the pod runs). Role knowledge ships as skills (how to do the job). `tk scion-taskforce skills install [<role>...]` turns roles from [scion-frontiers/agent-team](https://github.com/scion-frontiers/agent-team/tree/main/templates) into skills under `.agents/skills/`:

| Folder | Content |
| :--- | :--- |
| `tk-scion-<role>/SKILL.md` | The tk contract (wins over upstream: work alone, report in the ticket, follow the git rule, no push), the upstream persona (`system-prompt.md`), the role guidance (`agents.md`) and paths to its related skills |
| `tk-scion-<skill>/` | Each skill a role references, with `name:` set to the prefixed folder name and its own `LICENSE` |
| `UPSTREAM.md` (in each folder) | Source commit, licence and every installed or dropped skill; marks the folder as generated |

- Default set: `developer`, `code-reviewer`, `investigator`, `doc-writer`, `test-engineer`, `security-auditor`, `researcher`, `architect`. Name others explicitly (for example `qa-tester`). Coordinator roles are left out because `tk` is the coordinator.
- Upstream is fetched once at a pinned commit (`--ref <sha>` overrides), so nothing is downloaded when a worker starts. Per-role model and resource settings are not carried over.
- Re-running keeps existing skills. `--force` regenerates generated skills (those with `UPSTREAM.md`) only; hand-made skills and folders without the `tk-scion-` prefix are never touched. `uninit` removes generated skills.
- Offline or air-gapped: mirror the repos as `<dir>/<owner>/<repo>/`, then run `skills install --from <dir>`.
- Git: tk neither commits nor ignores the skills. Commit them to share (`git add .agents/skills/tk-scion-*`) or keep them local (`echo '/.agents/skills/tk-scion-*/' >> .git/info/exclude`). If Scion gives a worker its own worktree, that worktree holds only committed files, so commit the skills to use them there.
- The skills are plain `SKILL.md` files, so people and local agents can use them outside Scion too.

How the brief uses them (the brief names file paths, so this works with any harness):

| Ticket | Brief |
| :--- | :--- |
| Tagged `role:<name>` (several allowed) | "Read and follow `.agents/skills/tk-scion-<name>/SKILL.md` before starting" (mandatory) |
| No role tag | The installed role skills (and hand-made `tk-scion-*` skills) with descriptions; use one only if it clearly fits. Less reliable than a tag |
| Tagged with a role whose skill is missing | No worker starts. The ticket gets a note with the install command; the queue moves on to other tickets |

Custom briefs (`worker.prompt_file`) get the same section through the `{skills}` placeholder.

**Migrating from role templates.** `templates install` and `templates list` still work as deprecated aliases of `skills` (removal after 2027-04-01). Old generated `.scion/templates/tk-<role>/` templates keep working for a role that has no skill yet. To switch: run `tk scion-taskforce skills install`, then delete the old `tk-<role>` folders (`uninit` also removes them).

### tk inside workers

Worker images do not ship `tk`. At each start the task force finds `tk` on this machine and mounts it read-only at `/usr/local/bin/tk` in the worker. It checks `$TK_SCRIPT` (the `tk` that is running) first, then `tk` and `ticket` on `PATH`, so nothing machine-specific is stored in the project. The mount travels as a Scion launch config (`scion start --config`), saved next to the brief as `<id>.scion-config.json`. It also sets `TK_NO_HOOKS=1` inside the worker, because the shared checkout's save hook needs the plugin, which the container lacks.

If `tk` is not found, or `provider.mount_tk` is `false`, the worker edits `.tickets/<id>.md` directly. Turn the mount off when workers run on a remote Scion broker, where your local path does not exist.

The brief, the seeded template and the role skills tell workers to use `tk` as their only channel:

| Worker step | Command |
| :--- | :--- |
| Read the ticket and new feedback (again on each resume) | `tk show <id>`, `tk dep tree <id>` |
| Share progress or ask a question | `tk add-note <id> "..."` |
| Report | `tk add-note <id>` with a `## Task Force Worker Report` heading |
| Hand back for review | `tk update <id> --tags <current tags>,waiting-for-review` |

Workers never close, reopen or create tickets. `init` updates the old report section of an existing worker template in place; role skills update with `skills install --force`.

## Automatic actions

The task force fixes safe, reversible plumbing on its own and records each fix. `status` lists the latest five under *Automatic actions*; `logs` has them all.

| Action | When | Undo |
| :--- | :--- | :--- |
| Add `/.scion/agents/` to `.git/info/exclude` (Scion requires it in git repos; local, never committed) | `init`, and before each start | Delete the line |
| Run `tk init` / `scion init` | `init`, when missing | Remove `.tickets/` or `.scion/` |
| Seed the worker template; update its old git and report sections | `init` | Edit or delete the template |
| Link the folder to the Scion Hub | `init`; at dispatch only for a configured, unlinked project (`provider.auto_link_hub`) | `scion hub unlink` |
| Start the Podman machine (`podman machine start`); tk never stops it | Before a start, when the runtime is down (`provider.auto_start_runtime`) | `podman machine stop` |
| Stop or delete a worker | Close, untag, file delete, `gc` | Re-tag the ticket |

What only you can fix (Hub down, a runtime that will not start, missing credentials) appears as one ticket note with the next step, and under *Needs you* in `status`. Saving the ticket or running `sync` retries.

## Commands

```text
tk scion-taskforce [--config <path>] [--dry-run] <subcommand> [args...]
```

`--config` adds a config file on top of the others. `--dry-run` simulates every `scion` call.

| Command | Description |
| :--- | :--- |
| `tk scion-taskforce init [--global] [--force] [--defaults\|--interactive]` | Run `tk init`/`scion init` if needed, then the wizard: config, template, Hub link, save hook. `--global` writes only `~/.config/tk/scion-taskforce.yaml` |
| `tk scion-taskforce uninit [--global] [--yes]` | Stop and delete this project's workers (branches kept), then remove `.scion-taskforce/`, the worker template, generated `tk-scion-*` skills and the save hook. Asks first unless `--yes` |
| `tk scion-taskforce hook install\|uninstall\|status` | Manage the save hook for this project |
| `tk scion-taskforce test [--timeout <s>] [--keep]` | Create a ticket tagged `init,taskforce`, wait (default 600 s) for its worker to report back, then close it unless `--keep` |
| `tk scion-taskforce skills install [<role>...] [--force] [--from <dir>] [--ref <sha>]` | Install agent-team roles (default set) as `.agents/skills/tk-scion-*` skills; see [Role skills](#role-skills). `templates install` is a deprecated alias |
| `tk scion-taskforce skills list` | Installed `tk-scion-*` skills and their sources |
| `tk scion-taskforce on-save <id> [--event <e>]` | Handle one ticket save. The hook calls it |
| `tk scion-taskforce sync [dir]` | Merge worker reports, pause reviewed workers and workers that stopped without a report, flag dead workers, start queued tickets |
| `tk scion-taskforce watch [dir] [--interval <s>]` | Foreground loop: `sync` every `<s>` seconds (default 60, minimum 10) without retrying failed starts. Ctrl-C stops it |
| `tk scion-taskforce dispatch <id>` | Start a worker for one ready, opted-in ticket now, ignoring the worker limit |
| `tk scion-taskforce status` | Settings, save hook, provider health, workers, *Needs you* and the latest automatic actions |
| `tk scion-taskforce list \| ps` | All tracked workers across projects |
| `tk scion-taskforce feedback <id> "<msg>"` | Add a review note, wake the active worker and remove `waiting-for-review` |
| `tk scion-taskforce attach <id>` | Attach to the worker; a paused worker is resumed first |
| `tk scion-taskforce pause <id>` | Pause the worker |
| `tk scion-taskforce logs [<id>]` | Show `taskforce.log` or one worker's log, including rotated `.gz` files |
| `tk scion-taskforce brief <id>` | Show the brief the worker was started with |
| `tk scion-taskforce trace [<id>]` | Show trace spans, optionally for one ticket |
| `tk scion-taskforce gc [--force]` | Delete workers of tickets closed more than 5 days ago; purge rotated logs older than 30 days |
| `tk scion-taskforce version \| help` | Version and active config file, or usage |

The removed daemon commands (`start`, `stop`, `restart`, `server`, `project`) exit with code 2 and print what to use instead.

## Configuration

`init` writes the full key reference, with a comment on every key, to `.scion-taskforce/scion-taskforce.yaml`. Files are deep-merged, low to high:

1. Built-in defaults
2. `~/.config/tk/scion-taskforce.yaml` (or `$XDG_CONFIG_HOME/tk/`)
3. `<project>/.scion-taskforce/scion-taskforce.yaml`
4. The file in `$TK_SCION_TASKFORCE_CONFIG`
5. `--config <path>`

Commonly edited keys:

| Key | Default | Purpose |
| :--- | :--- | :--- |
| `tags.claim` | `taskforce` | Opt-in tag |
| `watcher.max_concurrent_per_project` | `1` | Running workers per project. Workers share the checkout, so keep 1 unless you accept that |
| `watcher.max_concurrent` | `10` | Running workers across all projects |
| `watcher.gc_retention_days` | `5` | Days after close before `gc` deletes a worker |
| `provider.harness_config` | `gemini-cli` | Scion harness |
| `provider.model` | blank | Model ID or Scion alias; aliases are resolved to an ID at start |
| `provider.gcp_project`, `provider.gcp_region` | blank | Vertex AI project and location |
| `provider.auto_start_runtime`, `provider.auto_link_hub` | `true` | Automatic Podman start and Hub link; see [Automatic actions](#automatic-actions) |
| `provider.mount_tk` | `true` | Mount this machine's `tk` into each worker; see [tk inside workers](#tk-inside-workers) |
| `worker.git` | `off` | `off`: no git state changes; `branch`: commit on the ticket branch |
| `worker.privacy` | `confidential` | `confidential` or `standard`; see [Privacy](#privacy) |
| `worker.prompt_file` | blank | Custom brief template; `{skills}` inserts the skill section |
| `telemetry.rotation.retention_days` | `30` | Days `gc` keeps rotated logs |

## Logs and state

| Path | Content |
| :--- | :--- |
| `.tickets/.hooks/hooks.log` | One summary line per save (git-ignored) |
| `~/.local/state/tk/scion-taskforce.json` | Worker state for all projects |
| `~/.local/state/tk/scion-taskforce/logs/taskforce.log` | Task force decisions and errors (`logs`) |
| `…/logs/otel-traces.jsonl`, `…/logs/otel-metrics.jsonl` | Spans (`trace`) and metrics |
| `…/logs/workers/<project>/<id>.log`, `<id>.brief.md` | Per-worker log (`logs <id>`) and brief (`brief <id>`) |
| `.tickets/.scion-taskforce-logs` | Symlink to the log directory |

Logs rotate daily (UTC) or at 100 MB. Set `TK_SCION_TASKFORCE_LOG_DIR` or `TK_SCION_TASKFORCE_STATE_DIR` to move them.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Saving a tagged ticket does nothing | Hook missing, ticket not ready, or `TK_NO_HOOKS` set | Run `tk scion-taskforce status`, read `.tickets/.hooks/hooks.log`, then `hook install` or `sync` |
| Note: "could not start a Scion worker … podman" | Container runtime down and `podman machine start` failed or is disabled | Start the runtime, then save the ticket again or run `sync` |
| Note: "not linked to the Scion Hub" | Folder has no task force config, or the link failed | Run `tk scion-taskforce init` once |
| Note: "'.scion/agents/' must be in .gitignore" | The automatic `.git/info/exclude` fix failed (for example, a read-only `.git`) | Add `/.scion/agents/` to `.git/info/exclude`, then save the ticket again |
| Note: "role skill `tk-scion-x` is not installed" | The ticket is tagged `role:x` but `.agents/skills/tk-scion-x/` is missing; no worker started | `tk scion-taskforce skills install x`, then save the ticket again or run `sync` |
| `skills install` cannot download | No network or GitHub rate limit | Set `GITHUB_TOKEN`, or use `--from <mirror>` |
| `skills install`: "exists and was not generated by tk" | A hand-made `tk-scion-<role>` folder has no `UPSTREAM.md` | Rename that folder, or install a different role |
| Worker reported, but the ticket shows nothing | Reports land on the next save | Run `tk scion-taskforce sync`, or keep `watch` running |
| Note: "stopped without a report" | The worker's turn ended (finished, asked a question, or hit a limit) without the review tag | Add a note to answer or redirect it; `attach <id>` shows the session |
| Note: "worker lost" | The pod died without reporting | Inspect with `logs <id>`. `tk reopen <id>` (tag kept) relaunches; remove the tag to abandon |
| `test` times out | Worker slow, stuck or queued | `tk scion-taskforce attach <id>` or `logs <id>`; the ticket stays open |
| Resumed worker fails with a model error such as `--model medium` | Older versions passed the alias to `scion resume` | Fixed: `start` now resolves aliases. To restart an old worker, remove `taskforce` and `waiting-for-review`, run `tk reopen <id>`, then add `taskforce` again |
| Worker fails to authenticate | Wrong credentials for the harness | `gemini-cli`: add `GEMINI_API_KEY` as a Hub secret. Vertex AI: `gcloud auth application-default login` and set `provider.gcp_project` |
| Ticket stays "queued" | All slots busy | Check `status`; close or review a worker, or run `dispatch <id>` |
| Error: "worker state file … is not valid JSON" | Corrupt state file | Fix or delete the file (a backup is kept), then `sync` |

## Uninstall

```bash
tk scion-taskforce uninit                         # per project: workers, config, template, hook
tk scion-taskforce uninit --global                # global config
./plugins/scion-taskforce/install.sh --uninstall  # remove the binaries
```
