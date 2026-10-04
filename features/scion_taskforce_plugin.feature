Feature: SCION Task Force Plugin
  As a developer or autonomous orchestrator
  I want ticket saves to hand opted-in tickets to SCION workers
  So that tickets are claimed only after a verified worker launch, paused for review,
  woken on feedback, and traced with OpenTelemetry

  Scenario: Help command discovers scion-taskforce plugin
    When I run "ticket help"
    Then the command should succeed
    And the output should contain "scion-taskforce"
    And the output should contain "Autonomous SCION task force orchestrator"

  Scenario: The user guide lists every command from the help text
    When I run "ticket scion-taskforce help"
    Then the command should succeed
    And every command line in the output should appear in the repo file "docs/plugins/scion-taskforce.md"

  Scenario: Initialize project scion-taskforce.yaml config
    Given a clean tickets directory
    When I run "ticket scion-taskforce init"
    Then the command should succeed
    And the output should contain "Initialization successful"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "claim: taskforce"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "ignore: no-taskforce"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "review: waiting-for-review"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "max_concurrent_per_project: 1"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "retention_days: 30"
    And the file ".scion-taskforce/prompt.md" should not exist

  Scenario: Re-running init keeps edited config values and template files
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    And I run "sed -i.bak 's/gc_retention_days: 5/gc_retention_days: 9/' .scion-taskforce/scion-taskforce.yaml"
    And I run "echo '# my edit' >> .scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md"
    And I run "ticket scion-taskforce init"
    Then the command should succeed
    And the output should contain "kept your existing values"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "gc_retention_days: 9"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should contain "# my edit"
    When I run "ls .scion-taskforce"
    Then the output should not contain ".old"
    When I run "ticket scion-taskforce init --force"
    Then the file ".scion-taskforce/scion-taskforce.yaml" should contain "gc_retention_days: 5"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should not contain "# my edit"

  Scenario: Re-running init replaces the old report section of the worker template with tk instructions
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    And I run "printf '%s\n' '# tk Task Force Worker' '' '## Report back' '- Record what you changed, how you verified it and any open questions as a note in' '  `.tickets/<id>.md` (use `tk add-note <id> \"...\"` when `tk` is installed).' '- Add the review tag named in your task prompt (default `waiting-for-review`), then stop. Review feedback arrives as a new note.' '' '# my edit' > .scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md"
    And I run "ticket scion-taskforce init"
    Then the command should succeed
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should contain "## Use tk for updates"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should contain "Read updates with `tk show <id>`"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should contain "# my edit"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should not contain "## Report back"

  Scenario: test --raw was removed and points to the ticket-based test
    Given a clean tickets directory
    When I run "ticket scion-taskforce test --raw"
    Then the exit code should be 2
    And the output should contain "`--raw` was removed; `tk scion-taskforce test` verifies end to end through a ticket"

  Scenario: Init wizard offers menus, validates input and saves Vertex AI project and region
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "printf '3\nclaude\nopencode\n\n2\nBad_Proj\nmy-proj-123\neu-central1\n4\n\n9\n1\n\n2\ny\nn\n' | GOOGLE_CLOUD_PROJECT=tk-detected-proj ticket scion-taskforce init --interactive"
    Then the command should succeed
    And the output should contain "Other (type a value)"
    And the output should contain "'claude' is not installed"
    And the output should contain "Project IDs are 6-30 chars"
    And the output should contain "looks like an AWS region"
    And the output should contain "choose 4 to type your own value"
    And the output should contain "scion init: created .scion/"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "opencode"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "vertex-ai"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "my-proj-123"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "europe-west4"

  Scenario: Init wizard defaults to gemini-cli with API-key auth and the standard worker template
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "printf '\n\n\n\n\n2\ny\nn\n' | ticket scion-taskforce init --interactive"
    Then the command should succeed
    And the output should contain "7. Privacy"
    And the output should contain "8. agent-team role templates"
    And the output should contain "recommended: API-key auth"
    And the output should contain "skipped; gemini-cli authenticates with the GEMINI_API_KEY Scion secret"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "api-key"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "tk-worker-gemini-cli-with-api-key-auth"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/scion-agent.yaml" should contain "agent_instructions: agents.md"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should contain "Git is optional: never run `git init`"

  Scenario: test verifies the task force through a real ticket and closes it
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    And I run "FAKE_SCION_WORKER_REPORT=1 TK_HOOKS_SYNC=1 ticket scion-taskforce test --timeout 20"
    Then the command should succeed
    And the output should contain "(tags: init, taskforce)"
    And the output should contain "started Scion worker"
    And the output should contain "fake worker report"
    And the output should contain "the task force works end to end"
    And the output should contain "its worker is stopped"

  Scenario: test times out and leaves the ticket open when no worker reports back
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    And I run "TK_HOOKS_SYNC=1 ticket scion-taskforce test --timeout 2"
    Then the command should fail
    And the output should contain "started Scion worker"
    And the output should contain "Timed out"

  Scenario: test requires the save hook
    Given a clean tickets directory
    When I run "ticket scion-taskforce test"
    Then the command should fail
    And the output should contain "Save hook not installed"

  Scenario: Quitting the init wizard changes nothing
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "printf 'q\n' | ticket scion-taskforce init --interactive"
    Then the command should fail
    And the output should contain "Setup cancelled; nothing was changed."
    And the file ".scion-taskforce/scion-taskforce.yaml" should not exist

  Scenario: Init runs tk init when the folder has no .tickets yet
    Given a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    Then the command should succeed
    And the output should contain "tk init: Initialized ticket repository"
    And the output should contain "Initialization successful"

  Scenario: In a git repo, .scion/agents/ goes to .git/info/exclude, never to .gitignore
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the project is a git repository
    And a file ".scion/settings.yaml" with content "schema_version: '1'"
    When I run "ticket scion-taskforce init"
    Then the command should succeed
    And the output should contain "auto-fix: added `/.scion/agents/`"
    And the file ".git/info/exclude" should contain "/.scion/agents/"
    And the file ".gitignore" should not exist
    When I run "ticket scion-taskforce init"
    Then the output should not contain "auto-fix"

  Scenario: A folder that becomes a git repo after init still dispatches, and status shows the auto-fix
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0005" and title "Git arrives later"
    And ticket "tf-0005" has tags "taskforce"
    When I run "ticket scion-taskforce init"
    Then the output should not contain "auto-fix"
    Given the project is a git repository
    When I run "ticket scion-taskforce dispatch tf-0005"
    Then the command should succeed
    And the file ".git/info/exclude" should contain "/.scion/agents/"
    When I run "ticket scion-taskforce status"
    Then the output should contain "Settings:  worker.git=off, worker.privacy=confidential, roles: none"
    And the output should contain "Needs you: nothing"
    And the output should contain "Automatic actions (latest 5):"
    And the output should contain "auto-fix: added `/.scion/agents/`"

  Scenario: templates install vendors agent-team roles with the tk contract
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a local agent-team mirror at "mirror"
    When I run "ticket scion-taskforce init"
    And I run "ticket scion-taskforce templates install developer --from mirror"
    Then the command should succeed
    And the output should contain "tk-developer: installed, 2 skill(s) vendored; dropped: gcs-artifact-publishing"
    And the file ".scion/templates/tk-developer/agents.md" should contain "tk contract (wins over the role guidance below)"
    And the file ".scion/templates/tk-developer/agents.md" should contain "Commit and push per logical phase"
    And the file ".scion/templates/tk-developer/skills/code-review/SKILL.md" should contain "name: code-review"
    And the file ".scion/templates/tk-developer/skills/code-simplification/LICENSE" should contain "MIT License"
    And the file ".scion/templates/tk-developer/skills/gcs-artifact-publishing/SKILL.md" should not exist
    And the file ".scion/templates/tk-developer/scion-agent.yaml" should not contain "uri:"
    And the file ".scion/templates/tk-developer/UPSTREAM.md" should contain "dropped: publishes public links"
    And the file ".scion/templates/tk-developer/LICENSE" should contain "Apache License"
    When I run "ticket scion-taskforce templates install developer --from mirror"
    Then the output should contain "tk-developer: kept"
    When I run "ticket scion-taskforce templates install ghost --from mirror"
    Then the command should fail
    And the output should contain "unknown role(s): ghost. Available: developer"
    When I run "ticket scion-taskforce templates list"
    Then the output should contain "developer"
    When I run "ticket scion-taskforce uninit --yes"
    Then the file ".scion/templates/tk-developer/agents.md" should not exist

  Scenario: A role tag runs the worker on its role template
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a local agent-team mirror at "mirror"
    And a ticket exists with ID "tf-0007" and title "Developer role"
    And ticket "tf-0007" has tags "taskforce, role:developer"
    When I run "ticket scion-taskforce init"
    And I run "ticket scion-taskforce templates install developer --from mirror"
    And I run "ticket scion-taskforce dispatch tf-0007"
    Then the command should succeed
    And the fake scion start for "tf-0007" should include "-t tk-developer"

  Scenario: A role tag without an installed template falls back to the default worker with a note
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0006" and title "Ghost role"
    And ticket "tf-0006" has tags "taskforce, role:ghost"
    When I run "ticket scion-taskforce dispatch tf-0006"
    Then the command should succeed
    And ticket "tf-0006" should contain "role `ghost` has no template in this project; using the default worker"
    And the fake scion start for "tf-0006" should not include "tk-ghost"

  Scenario: Task force is opt-in - only tickets the user tagged taskforce are dispatched
    Given a clean tickets directory
    And a ticket exists with ID "tf-0001" and title "Opted-in task"
    And ticket "tf-0001" has tags "taskforce"
    And a ticket exists with ID "tf-0002" and title "Untagged task"
    And a ticket exists with ID "tf-0003" and title "Opted out task"
    And ticket "tf-0003" has tags "taskforce, no-taskforce"
    When I run "ticket scion-taskforce sync --dry-run"
    Then the command should succeed
    And the output should contain "started=1"
    And ticket "tf-0001" should have field "status" with value "in_progress"
    And ticket "tf-0001" should contain "tags: [taskforce]"
    And ticket "tf-0002" should have field "status" with value "open"
    And ticket "tf-0002" should not contain "taskforce"
    And ticket "tf-0003" should have field "status" with value "open"

  Scenario: Dispatching a ticket without the opt-in tag is refused
    Given a clean tickets directory
    And a ticket exists with ID "tf-0005" and title "Not opted in"
    When I run "ticket scion-taskforce dispatch tf-0005 --dry-run"
    Then the command should fail
    And the output should contain "missing opt-in tag 'taskforce'"
    And ticket "tf-0005" should have field "status" with value "open"

  Scenario: Runtime down - spawn fails and tickets are left untouched (no fire-and-forget)
    Given a clean tickets directory
    And a fake "scion" runtime in mode "fail"
    And a ticket exists with ID "tf-0011" and title "First"
    And ticket "tf-0011" has tags "taskforce"
    And a ticket exists with ID "tf-0012" and title "Second"
    And ticket "tf-0012" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=0"
    And the output should contain "errors=1"
    And ticket "tf-0011" should have field "status" with value "open"
    And ticket "tf-0012" should have field "status" with value "open"
    When I run "ticket scion-taskforce status"
    Then the output should contain "Provider:  unavailable"
    And the output should contain "Needs you:"
    And the output should contain "- scion list exited 125: Error: podman ps failed"
    When I run "ticket scion-taskforce logs"
    Then the output should contain "Provider runtime UNAVAILABLE"

  Scenario: Spawn accepted but pod never becomes ready - ticket stays open and is not retried blindly
    Given a clean tickets directory
    And a fake "scion" runtime in mode "silent"
    And the scion-taskforce setting "watcher.spawn_verify_timeout_seconds" is "1"
    And the scion-taskforce setting "watcher.spawn_verify_poll_seconds" is "0.2"
    And a ticket exists with ID "tf-0021" and title "Ghost pod"
    And ticket "tf-0021" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0021"
    Then the command should fail
    And the output should contain "did not reach 'running' within 1s"
    And ticket "tf-0021" should have field "status" with value "open"
    When I run "ticket scion-taskforce list"
    Then the output should contain "tf-0021"
    And the output should contain "error"

  Scenario: Verified spawn against a healthy runtime claims the ticket
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0031" and title "Real work"
    And ticket "tf-0031" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0031"
    Then the command should succeed
    And the output should contain "Dispatched & verified task force worker 'tf-0031'"
    And ticket "tf-0031" should have field "status" with value "in_progress"
    And the fake scion runtime should have 1 pod(s)
    When I run "ticket scion-taskforce trace tf-0031"
    Then the output should contain "taskforce.worker.spawn"

  Scenario: At most N working tasks per project; the next starts when one finishes
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "watcher.max_concurrent_per_project" is "2"
    And a ticket exists with ID "tf-0041" and title "A" with priority 1
    And ticket "tf-0041" has tags "taskforce"
    And a ticket exists with ID "tf-0042" and title "B" with priority 1
    And ticket "tf-0042" has tags "taskforce"
    And a ticket exists with ID "tf-0043" and title "C" with priority 2
    And ticket "tf-0043" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=2"
    And ticket "tf-0041" should have field "status" with value "in_progress"
    And ticket "tf-0042" should have field "status" with value "in_progress"
    And ticket "tf-0043" should have field "status" with value "open"
    And the fake scion runtime should have 2 pod(s)
    Given ticket "tf-0041" has tags "taskforce, waiting-for-review"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "paused=1"
    And the output should contain "started=1"
    And ticket "tf-0043" should have field "status" with value "in_progress"
    And the fake scion runtime should have 3 pod(s)

  Scenario: Auto-pause on waiting-for-review and wake on feedback with OpenTelemetry traces
    Given a clean tickets directory
    And a ticket exists with ID "tf-0010" and title "Implement feature X"
    And ticket "tf-0010" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0010 --dry-run"
    Then the command should succeed
    And ticket "tf-0010" should have field "status" with value "in_progress"
    Given ticket "tf-0010" has tags "taskforce, waiting-for-review"
    When I run "ticket scion-taskforce sync --dry-run"
    Then the command should succeed
    And the output should contain "paused=1"
    When I run "ticket scion-taskforce feedback tf-0010 \"Please add unit tests\" --dry-run"
    Then the command should succeed
    And the output should contain "Feedback added to tf-0010, removed waiting-for-review, and woke worker"
    And ticket "tf-0010" should contain "**Review Feedback:** Please add unit tests"
    And ticket "tf-0010" should not contain "waiting-for-review"
    When I run "ticket scion-taskforce trace tf-0010"
    Then the command should succeed
    And the output should contain "taskforce.ticket.lifecycle"
    And the output should contain "taskforce.worker.spawn"
    And the output should contain "taskforce.worker.pause"
    And the output should contain "taskforce.worker.feedback_wake"
    When I run "ticket scion-taskforce logs tf-0010"
    Then the command should succeed
    And the output should contain "Worker tf-0010 spawned"
    And the output should contain "Worker tf-0010 paused"
    And the output should contain "Worker tf-0010 resumed with feedback"

  Scenario: Garbage collection deletes closed ticket worker pods and reports retention
    Given a clean tickets directory
    And a ticket exists with ID "tf-0020" and title "Completed task"
    And ticket "tf-0020" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0020 --dry-run"
    Then the command should succeed
    Given ticket "tf-0020" has status "closed"
    When I run "ticket scion-taskforce gc --force --dry-run"
    Then the command should succeed
    And the output should contain "deleted_closed_pods=1 (retention=5d)"
    And the output should contain "retention=30d"

  Scenario: gc keeps the worker entry when scion delete fails
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0022" and title "Delete fails"
    And ticket "tf-0022" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0022"
    Then the command should succeed
    Given ticket "tf-0022" has status "closed"
    And the environment variable "FAKE_SCION_FAIL_CMDS" is "delete"
    When I run "ticket scion-taskforce gc --force"
    Then the command should succeed
    And the output should contain "deleted_closed_pods=0"
    When I run "ticket scion-taskforce list"
    Then the output should contain "running"
    When I run "ticket scion-taskforce logs"
    Then the output should contain "GC could not delete worker pod tf-0022"
    Given the environment variable "FAKE_SCION_FAIL_CMDS" is ""
    When I run "ticket scion-taskforce gc --force"
    Then the output should contain "deleted_closed_pods=1"
    And the fake scion runtime should have 0 pod(s)

  Scenario: A pull-request ticket gets a review brief, a normal ticket gets an implementation brief
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "watcher.max_concurrent_per_project" is "2"
    And a ticket exists with ID "tf-0071" and title "Review: add retry to client"
    And ticket "tf-0071" has tags "github-sync, pr, taskforce"
    And ticket "tf-0071" has external ref "gh-pr-2246"
    And a ticket exists with ID "tf-0072" and title "Implement retry in client"
    And ticket "tf-0072" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=2"
    And the fake scion prompt for "tf-0071" should contain "Your Job: Pull-Request Review"
    And the fake scion prompt for "tf-0071" should contain "gh pr diff 2246"
    And the fake scion prompt for "tf-0071" should contain "Do not check out the PR branch"
    And the fake scion prompt for "tf-0071" should not contain "gh pr comment"
    And the fake scion prompt for "tf-0071" should not contain "Your Job: Implementation"
    And the fake scion prompt for "tf-0071" should contain "tk update tf-0071 --tags github-sync,pr,taskforce,waiting-for-review"
    And the fake scion prompt for "tf-0072" should contain "Your Job: Implementation"
    And the fake scion prompt for "tf-0072" should contain "The ticket is your channel: use `tk`"
    And the fake scion prompt for "tf-0072" should contain "tk show tf-0072"
    And the fake scion prompt for "tf-0072" should contain "tk add-note tf-0072"
    And the fake scion prompt for "tf-0072" should contain "tk update tf-0072 --tags taskforce,waiting-for-review"
    And the fake scion prompt for "tf-0072" should contain "Git is optional here. Do not change git state"
    And the fake scion prompt for "tf-0072" should contain "Do not commit; list the files you changed"
    And the fake scion prompt for "tf-0072" should contain "Confidentiality (this project is confidential)"
    And the fake scion start for "tf-0072" should not include "--branch"

  Scenario: worker.git branch and worker.privacy standard restore branch commits and PR comments
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "watcher.max_concurrent_per_project" is "2"
    And the scion-taskforce setting "worker.git" is "branch"
    And the scion-taskforce setting "worker.privacy" is "standard"
    And a ticket exists with ID "tf-0073" and title "Review: add retry to client"
    And ticket "tf-0073" has tags "pr, taskforce"
    And ticket "tf-0073" has external ref "gh-pr-2246"
    And a ticket exists with ID "tf-0074" and title "Implement retry in client"
    And ticket "tf-0074" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "started=2"
    And the fake scion prompt for "tf-0073" should contain "gh pr checkout 2246"
    And the fake scion prompt for "tf-0073" should contain "never approve/merge"
    And the fake scion prompt for "tf-0074" should contain "do NOT push, merge, rebase onto other branches, or"
    And the fake scion prompt for "tf-0074" should not contain "Confidentiality"
    And the fake scion start for "tf-0074" should include "--branch tf-0074"

  Scenario: A custom worker.prompt_file template overrides the built-in brief
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "worker.prompt_file" is ".tickets/worker-prompt.md"
    And a file ".tickets/worker-prompt.md" with content "CUSTOM BRIEF for {ticket_id} ({work_type}): {ticket_title}"
    And a ticket exists with ID "tf-0075" and title "Custom prompt ticket"
    And ticket "tf-0075" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0075"
    Then the command should succeed
    And the fake scion prompt for "tf-0075" should contain "CUSTOM BRIEF for tf-0075 (implement): Custom prompt ticket"
    And the fake scion prompt for "tf-0075" should not contain "Your Job"

  Scenario: A Scion model alias is resolved before start so resumed workers keep a valid model
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "provider.harness_config" is "gemini-cli"
    And the scion-taskforce setting "provider.model" is "medium"
    And a file ".scion-home/harness-configs/gemini-cli/config.yaml" with content "{model_aliases: {medium: gemini-3.5-flash}}"
    And a ticket exists with ID "tf-0076" and title "Alias ticket"
    And ticket "tf-0076" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0076"
    Then the command should succeed
    And the fake scion start for "tf-0076" should include "--model gemini-3.5-flash"

  Scenario: A worker whose pod dies without reporting back is flagged, noted on the ticket, and frees its slot
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0081" and title "Will crash"
    And ticket "tf-0081" has tags "taskforce"
    And a ticket exists with ID "tf-0082" and title "Waiting for a slot"
    And ticket "tf-0082" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=1"
    And ticket "tf-0081" should have field "status" with value "in_progress"
    And ticket "tf-0082" should have field "status" with value "open"
    Given the fake scion pod "tf-0081" is in state "stopped"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "lost=1"
    And ticket "tf-0081" should contain "Task Force: worker lost"
    And ticket "tf-0081" should contain "tk reopen tf-0081"
    And ticket "tf-0081" should have field "status" with value "in_progress"
    And ticket "tf-0082" should have field "status" with value "in_progress"
    When I run "ticket scion-taskforce list"
    Then the output should contain "tf-0081"
    And the output should contain "error"

  Scenario: Reopening a lost ticket replaces the dead pod and relaunches it
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0085" and title "Lost then retried"
    And ticket "tf-0085" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "started=1"
    Given the fake scion pod "tf-0085" is in state "stopped"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "lost=1"
    When I run "ticket reopen tf-0085"
    And I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=1"
    And ticket "tf-0085" should have field "status" with value "in_progress"
    And the fake scion runtime should have 1 pod(s)
    When I run "ticket scion-taskforce logs"
    Then the output should contain "Replaced stale 'paused' pod for tf-0085"

  Scenario: Notes and the review tag written in a worker's isolated workspace are merged back into the project ticket
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0090" and title "Isolated worktree job"
    And ticket "tf-0090" has tags "taskforce"
    And a file ".scion/agents/tf-0090/workspace/.keep" with content "simulated scion worktree"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "started=1"
    When I run "ticket scion-taskforce logs"
    Then the output should contain "isolated workspace"
    Given I am in subdirectory ".scion/agents/tf-0090/workspace"
    When I run "ticket add-note tf-0090 'Worker report: diff is ready on branch tf-0090'"
    And I run "ticket update tf-0090 --tags taskforce,waiting-for-review"
    Then the command should succeed
    And ticket "tf-0090" should have field "status" with value "in_progress"
    Given I am back in the root directory
    When I run "ticket scion-taskforce sync"
    Then the output should contain "paused=1"
    When I run "ticket show tf-0090"
    Then the output should contain "waiting-for-review"
    And the output should contain "Worker report: diff is ready on branch tf-0090"
    When I run "ticket scion-taskforce logs"
    Then the output should contain "tf-0090: merged 1 note(s) and the 'waiting-for-review' tag from the worker workspace"

  Scenario: Persisted worker brief can be viewed via tk scion-taskforce brief
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0100" and title "Brief test task"
    And ticket "tf-0100" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0100"
    Then the command should succeed
    When I run "ticket scion-taskforce brief tf-0100"
    Then the command should succeed
    And the output should contain "You are an autonomous SCION task force worker assigned to ticket `tf-0100`"
    And the output should contain "Brief test task"

  Scenario: The per-project worker limit is honored even when .scion/ exists
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a file ".scion/config" with content "simulated worktree project"
    And a ticket exists with ID "tf-0101" and title "W1" with priority 1
    And ticket "tf-0101" has tags "taskforce"
    And a ticket exists with ID "tf-0102" and title "W2" with priority 1
    And ticket "tf-0102" has tags "taskforce"
    And a ticket exists with ID "tf-0103" and title "W3" with priority 1
    And ticket "tf-0103" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=1"
    And the fake scion runtime should have 1 pod(s)

  Scenario: Dispatch never links an unconfigured project folder to the Scion Hub
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the fake Scion Hub reports the project as "unlinked"
    And a ticket exists with ID "tf-0111" and title "Unlinked project task"
    And ticket "tf-0111" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0111"
    Then the command should fail
    And the output should contain "not linked to the Scion Hub"
    And the output should contain "tk scion-taskforce init"
    And ticket "tf-0111" should have field "status" with value "open"
    And the fake Scion Hub should have received "link" 0 time(s)
    And the fake scion runtime should have 0 pod(s)

  Scenario: Dispatch links a configured project to the Scion Hub and records the auto-fix
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the fake Scion Hub reports the project as "unlinked"
    And the scion-taskforce setting "tags.claim" is "taskforce"
    And a ticket exists with ID "tf-0112" and title "Configured project task"
    And ticket "tf-0112" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0112"
    Then the command should succeed
    And the fake Scion Hub should have received "link" 1 time(s)
    And the fake scion runtime should have 1 pod(s)
    When I run "ticket scion-taskforce status"
    Then the output should contain "auto-fix: linked this configured project to the Scion Hub"

  Scenario: Dispatch starts a stopped Podman machine, then the worker
    Given a clean tickets directory
    And a fake "scion" runtime in mode "fail"
    And the environment variable "FAKE_PODMAN_MODE" is "ok"
    And a ticket exists with ID "tf-0113" and title "Runtime was down"
    And ticket "tf-0113" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "started=1"
    And ticket "tf-0113" should have field "status" with value "in_progress"
    When I run "ticket scion-taskforce status"
    Then the output should contain "auto-fix: started the Podman machine"

  Scenario: Podman auto-start can be turned off
    Given a clean tickets directory
    And a fake "scion" runtime in mode "fail"
    And the environment variable "FAKE_PODMAN_MODE" is "ok"
    And the scion-taskforce setting "provider.auto_start_runtime" is "false"
    And a ticket exists with ID "tf-0114" and title "Stay down"
    And ticket "tf-0114" has tags "taskforce"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "started=0"
    And ticket "tf-0114" should have field "status" with value "open"

  Scenario: Init links the project folder to the Scion Hub exactly once
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the fake Scion Hub reports the project as "unlinked"
    When I run "ticket scion-taskforce init"
    Then the command should succeed
    And the output should contain "project linked to the Scion Hub"
    When I run "ticket scion-taskforce init --force"
    Then the command should succeed
    And the output should contain "project already linked to the Scion Hub"
    And the fake Scion Hub should have received "link" 1 time(s)

  Scenario: Init installs the save hook and uninit removes it
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    Then the command should succeed
    And the file ".tickets/.hooks/post-write.d/scion-taskforce" should contain "scion-taskforce on-save"
    And the file ".tickets/.hooks/.gitignore" should contain "post-write.d/scion-taskforce"
    And the file ".tickets/.gitignore" should contain ".scion-taskforce-logs"
    When I run "ticket scion-taskforce hook status"
    Then the output should contain "installed"
    When I run "ticket scion-taskforce uninit"
    Then the output should contain "Removed save hook"
    When I run "ticket scion-taskforce hook status"
    Then the output should contain "not installed"

  Scenario: uninit asks before stopping workers and --yes deletes them first
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce init"
    And I run "ticket create 'Busy' --tags taskforce"
    And I run "ticket scion-taskforce sync"
    Then the fake scion runtime should have 1 pod(s)
    When I run "printf 'n\n' | ticket scion-taskforce uninit"
    Then the command should fail
    And the output should contain "stops and deletes 1 Scion worker(s)"
    And the output should contain "Aborted; nothing was changed"
    And the fake scion runtime should have 1 pod(s)
    And the file ".tickets/.hooks/post-write.d/scion-taskforce" should contain "on-save"
    When I run "ticket scion-taskforce uninit --yes"
    Then the command should succeed
    And the output should contain "Stopped and deleted 1 worker(s)"
    And the output should contain "Removed save hook"
    And the fake scion runtime should have 0 pod(s)

  Scenario: Removed daemon commands fail with a migration hint
    Given a clean tickets directory
    When I run "ticket scion-taskforce start"
    Then the command should fail
    And the output should contain "`start` was removed: the polling daemon is gone"
    And the output should contain "tk scion-taskforce hook install"
    When I run "ticket scion-taskforce stop --all"
    Then the command should fail
    And the output should contain "tk scion-taskforce pause <id>"

  Scenario: sync warns when the save hook is not installed
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "Save hook not installed"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket scion-taskforce sync"
    Then the output should not contain "Save hook not installed"

  Scenario: Tagging a ready ticket starts a worker on save
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0201" and title "Event driven job"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0201 --tags taskforce"
    Then the command should succeed
    And ticket "tf-0201" should contain "Task Force:** request noted; no existing worker found"
    And ticket "tf-0201" should contain "started Scion worker `tf-0201`."
    And the fake scion start for "tf-0201" should not include "--branch"
    And ticket "tf-0201" should have field "status" with value "in_progress"
    And the fake scion runtime should have 1 pod(s)

  Scenario: Saving an untagged ticket does nothing
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0205" and title "Not for the task force"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0205 --priority 1"
    Then ticket "tf-0205" should not contain "Task Force:"
    And ticket "tf-0205" should have field "status" with value "open"
    And the fake scion runtime should have 0 pod(s)

  Scenario: A tagged ticket queues when slots are full and starts when a worker reports back
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0211" and title "First"
    And a ticket exists with ID "tf-0212" and title "Second"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0211 --tags taskforce"
    And I run "ticket update tf-0212 --tags taskforce"
    Then ticket "tf-0212" should contain "queued (1 of 1 workers busy)"
    And ticket "tf-0212" should have field "status" with value "open"
    When I run "ticket update tf-0211 --tags taskforce,waiting-for-review"
    Then ticket "tf-0212" should contain "a worker slot is free; starting a new Scion worker"
    And ticket "tf-0212" should have field "status" with value "in_progress"
    And the fake scion runtime should have 2 pod(s)

  Scenario: A note on a ticket with an active worker is forwarded once; status notes are not
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0221" and title "Needs feedback"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0221 --tags taskforce"
    And I run "ticket add-note tf-0221 'Please also add tests'"
    And I run "ticket update tf-0221 --priority 1"
    Then ticket "tf-0221" should contain "already in progress; forwarded the latest update" 1 time(s)
    And the fake scion runtime should have 1 pod(s)

  Scenario: Closing a ticket stops its worker
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0231" and title "Done soon"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0231 --tags taskforce"
    And I run "ticket close tf-0231"
    Then ticket "tf-0231" should contain "ticket closed; stopped worker `tf-0231`"
    And the fake scion pod "tf-0231" should be in state "stopped"

  Scenario: Removing the taskforce tag stops and removes the worker and notes it
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0232" and title "Changed my mind"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0232 --tags taskforce"
    Then the fake scion runtime should have 1 pod(s)
    When I run "ticket update tf-0232 --tags docs"
    Then ticket "tf-0232" should contain "`taskforce` tag removed; stopped and removed worker `tf-0232`."
    And the fake scion runtime should have 0 pod(s)

  Scenario: Adding the no-taskforce tag stops and removes the worker
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0233" and title "Hands off"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0233 --tags taskforce"
    And I run "ticket update tf-0233 --tags taskforce,no-taskforce"
    Then ticket "tf-0233" should contain "`no-taskforce` tag added; stopped and removed worker"
    And the fake scion runtime should have 0 pod(s)

  Scenario: Deleting a ticket file removes its worker and frees the slot
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0234" and title "Deleted soon"
    And a ticket exists with ID "tf-0235" and title "Queued behind it"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0234 --tags taskforce"
    And I run "ticket update tf-0235 --tags taskforce"
    Then ticket "tf-0235" should contain "queued (1 of 1 workers busy)"
    Given the file ".tickets/tf-0234.md" is deleted
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=1"
    And the fake scion pod "tf-0235" should be in state "running"
    And the fake scion runtime should have 1 pod(s)

  Scenario: A tagged ticket waiting on dependencies starts when the blocker closes
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0250" and title "Blocker"
    And a ticket exists with ID "tf-0251" and title "Blocked"
    And ticket "tf-0251" depends on "tf-0250"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0251 --tags taskforce"
    Then ticket "tf-0251" should contain "waiting on dependencies: tf-0250"
    And the fake scion runtime should have 0 pod(s)
    When I run "ticket close tf-0250"
    Then ticket "tf-0251" should have field "status" with value "in_progress"
    And the fake scion runtime should have 1 pod(s)

  Scenario: sync catches up on a worker report written straight to the file
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0241" and title "Worker reports by file"
    And a ticket exists with ID "tf-0242" and title "Queued behind it"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0241 --tags taskforce"
    And I run "ticket update tf-0242 --tags taskforce"
    Given ticket "tf-0241" has tags "taskforce, waiting-for-review"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "started=1"
    And ticket "tf-0242" should have field "status" with value "in_progress"

  Scenario: A failed start is retried on its own save, not on saves of other tickets
    Given a clean tickets directory
    And a fake "scion" runtime in mode "fail"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0261" and title "Fails to start"
    And a ticket exists with ID "tf-0262" and title "Unrelated"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0261 --tags taskforce"
    Then ticket "tf-0261" should contain "could not start a Scion worker" 1 time(s)
    And ticket "tf-0261" should contain "(see `tk scion-taskforce logs tf-0261`)"
    When I run "ticket update tf-0262 --priority 1"
    And I run "ticket add-note tf-0262 'unrelated change'"
    Then ticket "tf-0261" should contain "could not start a Scion worker" 1 time(s)
    And ticket "tf-0261" should contain "request noted" 1 time(s)
    When I run "ticket update tf-0261 --priority 1"
    Then ticket "tf-0261" should contain "could not start a Scion worker" 2 time(s)

  Scenario: Untagging a ticket whose worker never started writes no removal note
    Given a clean tickets directory
    And a fake "scion" runtime in mode "fail"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0263" and title "Never started"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0263 --tags taskforce"
    Then ticket "tf-0263" should contain "could not start a Scion worker" 1 time(s)
    When I run "ticket update tf-0263 --tags docs"
    Then ticket "tf-0263" should not contain "could not remove worker"
    And ticket "tf-0263" should not contain "stopped and removed worker"

  Scenario: A failed stop keeps the worker's slot and notes only a short reason
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0271" and title "Stop fails"
    And a ticket exists with ID "tf-0272" and title "Queued behind it"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0271 --tags taskforce"
    And I run "ticket update tf-0272 --tags taskforce"
    Given the environment variable "FAKE_SCION_FAIL_CMDS" is "stop,suspend"
    When I run "ticket close tf-0271"
    Then ticket "tf-0271" should contain "could not stop worker `tf-0271`: scion stop exited 1: Error: stop failed: simulated failure"
    And ticket "tf-0271" should not contain "second line with detail"
    And ticket "tf-0272" should have field "status" with value "open"
    And the fake scion pod "tf-0271" should be in state "running"
    When I run "ticket scion-taskforce logs tf-0271"
    Then the output should contain "second line with detail"

  Scenario: A failed suspend keeps the worker running and its slot taken
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0281" and title "Suspend fails"
    And a ticket exists with ID "tf-0282" and title "Queued behind it"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0281 --tags taskforce"
    And I run "ticket update tf-0282 --tags taskforce"
    Given the environment variable "FAKE_SCION_FAIL_CMDS" is "stop,suspend"
    When I run "ticket update tf-0281 --tags taskforce,waiting-for-review"
    Then ticket "tf-0281" should contain "could not pause worker `tf-0281`"
    And ticket "tf-0282" should have field "status" with value "open"
    And the fake scion runtime should have 1 pod(s)

  Scenario: feedback needs an active worker, changes the ticket only after a successful wake, and never re-adds the opt-in tag
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0291" and title "No worker yet"
    When I run "ticket scion-taskforce feedback tf-0291 \"Please fix\""
    Then the command should fail
    And the output should contain "has no active worker"
    And ticket "tf-0291" should not contain "Review Feedback"
    Given a ticket exists with ID "tf-0292" and title "Worker reported back"
    And ticket "tf-0292" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0292"
    Then the command should succeed
    Given ticket "tf-0292" has tags "waiting-for-review"
    And the environment variable "FAKE_SCION_FAIL_CMDS" is "message,resume"
    When I run "ticket scion-taskforce feedback tf-0292 \"Please add tests\""
    Then the command should fail
    And the output should contain "the ticket was not changed"
    And ticket "tf-0292" should contain "waiting-for-review"
    And ticket "tf-0292" should not contain "Review Feedback"
    Given the environment variable "FAKE_SCION_FAIL_CMDS" is ""
    When I run "ticket scion-taskforce feedback tf-0292 \"Please add tests\""
    Then the command should succeed
    And ticket "tf-0292" should contain "**Review Feedback:** Please add tests"
    And ticket "tf-0292" should not contain "waiting-for-review"
    And ticket "tf-0292" should not contain "taskforce"
    Given ticket "tf-0292" has status "closed"
    When I run "ticket scion-taskforce feedback tf-0292 \"More\""
    Then the command should fail
    And the output should contain "is closed"

  Scenario: on-save matches the saved ticket ID exactly
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0301" and title "Similar ID"
    And ticket "tf-0301" has tags "taskforce"
    When I run "ticket scion-taskforce on-save tf-030 --event delete"
    Then the command should succeed
    And the output should contain "tf-030: not found"
    And the fake scion runtime should have 0 pod(s)

  Scenario: A corrupt worker state file is backed up and reported, not silently reset
    Given a clean tickets directory
    And a file ".state/scion-taskforce.json" with content "{not json"
    When I run "ticket scion-taskforce sync"
    Then the command should fail
    And the output should contain "is not valid JSON; a copy is at"

  Scenario: sync pauses a worker whose turn ended without a report and frees its slot
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And the scion-taskforce setting "watcher.turn_grace_seconds" is "0"
    And a ticket exists with ID "tf-0301" and title "Stops without a report"
    And a ticket exists with ID "tf-0302" and title "Queued behind it"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0301 --tags taskforce"
    And I run "ticket update tf-0302 --tags taskforce"
    Then ticket "tf-0302" should have field "status" with value "open"
    Given the environment variable "FAKE_SCION_ACTIVITY" is "completed"
    When I run "ticket scion-taskforce sync"
    Then the command should succeed
    And the output should contain "paused=1"
    And the output should contain "started=1"
    And ticket "tf-0301" should contain "stopped without a report (Scion activity: completed); paused it"
    And the fake scion pod "tf-0301" should be in state "suspended"
    And ticket "tf-0302" should have field "status" with value "in_progress"

  Scenario: sync ignores a finished turn during the grace period
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And a ticket exists with ID "tf-0303" and title "Just started"
    When I run "ticket scion-taskforce hook install"
    And I run "ticket update tf-0303 --tags taskforce"
    Given the environment variable "FAKE_SCION_ACTIVITY" is "completed"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "paused=0"
    And ticket "tf-0303" should not contain "stopped without a report"
    And the fake scion pod "tf-0303" should be in state "running"

  Scenario: sync merges the report of a worker whose turn ended and adds no extra note
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the environment variable "TK_HOOKS_SYNC" is "1"
    And the environment variable "FAKE_SCION_WORKER_REPORT" is "1"
    And the scion-taskforce setting "watcher.turn_grace_seconds" is "0"
    And a ticket exists with ID "tf-0304" and title "Reports in its workspace"
    When I run "ticket scion-taskforce hook install"
    And I run "TK_NO_HOOKS=1 ticket update tf-0304 --tags taskforce"
    And I run "ticket scion-taskforce dispatch tf-0304"
    Given the environment variable "FAKE_SCION_ACTIVITY" is "completed"
    When I run "ticket scion-taskforce sync"
    Then the output should contain "paused=1"
    And ticket "tf-0304" should contain "fake worker report"
    And ticket "tf-0304" should not contain "stopped without a report"
    And the fake scion pod "tf-0304" should be in state "suspended"

  Scenario: watch rejects an interval below 10 seconds
    Given a clean tickets directory
    When I run "ticket scion-taskforce watch --interval 5"
    Then the command should fail
    And the output should contain "--interval takes a number of seconds >= 10"

  Scenario: Workers get this machine's tk, found at launch and mounted read-only
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0311" and title "Needs tk in the pod"
    And ticket "tf-0311" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0311"
    Then the command should succeed
    And the fake scion start for "tf-0311" should include "--config"
    And the fake scion launch config for "tf-0311" should contain "{tk}"
    And the fake scion launch config for "tf-0311" should contain "/usr/local/bin/tk"
    And the fake scion launch config for "tf-0311" should contain "TK_NO_HOOKS"

  Scenario: provider.mount_tk false starts workers without the tk mount
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "provider.mount_tk" is "false"
    And a ticket exists with ID "tf-0312" and title "No tk mount"
    And ticket "tf-0312" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0312"
    Then the command should succeed
    And the fake scion start for "tf-0312" should not include "--config"
