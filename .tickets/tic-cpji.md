---
tags: [taskforce]
id: tic-cpji
status: in_progress
deps: []
links: []
created: 2026-10-03T23:46:17Z
type: task
priority: 1
assignee: scion-agent
---
# feat: update the default for `tk-scion-taskforce init` and more

1. Update the default for `tk-scion-taskforce init` 

```
[build | demo | share] $ tk-scion-taskforce init
============================================================
🚀 SCION Task Force Setup Wizard
============================================================
Configure your project-level worker template & orchestrator.
Press [Enter] to accept the recommended default in brackets.

1. SCION Harness Engine [claude]: opencode
2. Default Model (Model Garden / Vertex AI, blank for default) []:
3. Google Cloud Project ID [gemini-demo-project-4242]:
4. Google Cloud Region [us-east5]: eu-central1
5. Task Opt-in Tag [taskforce]:
6. Max Concurrent Workers [1]:
```

Instead of just giving a text input options like `1. SCION Harness Engine [claude]`, can you provide a list of options to select. Add `Other` as last option to take manual input. Also do data validation check to input value is acceptable or not and then get correct one or provide option to exit. use `eu-central1` as default location and other popular option is `global`

Same job for `Default Model`, and other. 

2.  When I run `tk-scion-taskforce init` , do a quick check if (a) `tk init` and (b) `scion init` are done. If not run them as part of this executions. So user can just do `tk-scion-taskforce init` and all the check will be part of it. 

3. I do not see that you are asking for which model to use. curious  which model are you set to use.


## Notes

**2026-10-04T13:35:07Z**

**Task Force:** a worker slot is free; starting a new Scion worker.

**2026-10-04T13:35:49Z**

**Task Force:** started Scion worker `tic-cpji` on branch `tic-cpji`.

**2026-10-04T13:47:43Z**

Implemented in the main checkout (worker paused: opencode had no model set, so it chose 'Nano Banana Pro' via AI Studio and failed with a missing API key).
1. Wizard: numbered menus, Other for free text, validation with re-ask, q to quit, summary confirmation. Region default europe-west3 (Frankfurt). eu-central1 is an AWS region name; the wizard rejects it with that hint. global, eu, europe-west4, us-central1 and us-east5 are listed.
2. init runs tk init if .tickets/ is missing and scion init if .scion/ is missing.
3. Model: now asked. Options are the harness's Scion aliases, the harness default, and Vertex Gemini IDs for opencode. Project and region are now saved (provider.gcp_project/gcp_region); before this they were lost after the wizard.
Files: wizard.py (new), cli.py, config.py, providers/scion.py, feature tests (+3), docs.
