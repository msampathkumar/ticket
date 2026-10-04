---
title: SCION Task Force
description: Hand tk tickets to SCION coding agents through a save hook, then review and close.
---

Hand a ticket to an AI coding agent: tag it `taskforce`, and saving it starts a [SCION](https://github.com/GoogleCloudPlatform/scion) worker on its own branch. You review the worker's report on the ticket, then close the ticket, which stops the worker.

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

`tk scion-taskforce init` runs `tk init` when `.tickets/` is missing and `scion init` when `.scion/` is missing. In a terminal it then asks six questions. Each is a numbered menu: Enter takes the default (`*`), `Other` takes typed input, and `q` quits without changes. You confirm a summary before anything is written.

| # | Question | Options | Validation |
| :--- | :--- | :--- | :--- |
| 1 | Harness | From `scion harness-config list`. Default `gemini-cli`, else Scion's `default_harness_config` | Must be installed |
| 2 | Model | The harness's aliases (`small`, `medium`, `large`) or its default. `opencode` also lists `google-vertex/` Gemini IDs | No quotes or backslashes |
| 3 | Google Cloud project | Detected from `GOOGLE_CLOUD_PROJECT` or `gcloud`. Skipped for `gemini-cli` | Project ID format |
| 4 | Vertex AI location | `europe-west3` (default), `global`, `eu`, `europe-west4`, `us-central1`, `us-east5`. Skipped for `gemini-cli` | Google Cloud location; AWS-style names are rejected |
| 5 | Opt-in tag | `taskforce` | Letters, digits, `-_.` |
| 6 | Max concurrent workers per project | 1 (recommended), 2, 3 | 1–10 |

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
| `.tickets/.hooks/post-write.d/scion-taskforce` | The save hook |
| `.tickets/.hooks/.gitignore`, `.tickets/.gitignore` | Ignore the hook log, the hook and the log symlink |

`init` also links the folder to the Scion Hub once (`scion hub link`); dispatch never does. Re-running `init` keeps your config values and template edits. `--defaults` skips the questions; `--force` starts over.

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
| loses the `taskforce` tag or gains `no-taskforce` | Stops and deletes the worker (branch kept) and notes it |
| is deleted (seen on the next save or `sync`) | Stops and deletes the worker (branch kept) |

`tk scion-taskforce gc` deletes the stopped workers of tickets closed more than `watcher.gc_retention_days` (5) days ago.

Status notes start with `**Task Force:**`. They are written straight to the file, so they never re-trigger the hook and are never forwarded.

Writes that bypass `tk` fire no hook: hand edits, `git pull` and worker edits. A worker's report therefore lands on the next save of any ticket in the project. Run `tk scion-taskforce sync` to catch up at once. It also flags workers whose pods died.

## Commands

```text
tk scion-taskforce [--config <path>] [--dry-run] <subcommand> [args...]
```

`--config` adds a config file on top of the others. `--dry-run` simulates every `scion` call.

| Command | Description |
| :--- | :--- |
| `tk scion-taskforce init [--global] [--force] [--defaults\|--interactive]` | Run `tk init`/`scion init` if needed, then the wizard: config, template, Hub link, save hook. `--global` writes only `~/.config/tk/scion-taskforce.yaml` |
| `tk scion-taskforce uninit [--global] [--yes]` | Stop and delete this project's workers (branches kept), then remove `.scion-taskforce/`, the worker template and the save hook. Asks first unless `--yes` |
| `tk scion-taskforce hook install\|uninstall\|status` | Manage the save hook for this project |
| `tk scion-taskforce test [--timeout <s>] [--keep]` | Create a ticket tagged `init,taskforce`, wait (default 600 s) for its worker to report back, then close it unless `--keep` |
| `tk scion-taskforce on-save <id> [--event <e>]` | Handle one ticket save. The hook calls it |
| `tk scion-taskforce sync [dir]` | Merge worker reports, pause reviewed workers, flag dead workers, start queued tickets |
| `tk scion-taskforce dispatch <id>` | Start a worker for one ready, opted-in ticket now, ignoring the worker limit |
| `tk scion-taskforce status` | Save hook, provider health and workers for this project |
| `tk scion-taskforce list \| ps` | All tracked workers across projects |
| `tk scion-taskforce feedback <id> "<msg>"` | Add a review note, wake the active worker and remove `waiting-for-review` |
| `tk scion-taskforce attach <id>` | Attach to the worker; a paused worker is resumed first |
| `tk scion-taskforce pause <id>` | Pause the worker |
| `tk scion-taskforce logs [<id>]` | Show `taskforce.log` or one worker's log, including rotated `.gz` files |
| `tk scion-taskforce brief <id>` | Show the brief the worker was started with |
| `tk scion-taskforce trace [<id>]` | Show trace spans, optionally for one ticket |
| `tk scion-taskforce gc [--force]` | Delete workers of tickets closed more than 5 days ago; purge rotated logs older than 30 days |
| `tk scion-taskforce version \| help` | Version and active config file, or usage |

The removed daemon commands (`start`, `stop`, `restart`, `server`, `watch`, `project`) exit with code 2 and print what to use instead.

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
| `worker.prompt_file` | blank | Custom brief template |
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
| Note: "could not start a Scion worker … podman" | Container runtime down | `podman machine start`, then save the ticket again or run `sync` |
| Note: "not linked to the Scion Hub" | Folder never linked | Run `tk scion-taskforce init` once |
| Note: "'agents/' must be in .gitignore" | `scion init` never ran | Run `scion init` in the project |
| Worker reported, but the ticket shows nothing | Reports land on the next save | Run `tk scion-taskforce sync` |
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
