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
    And the file ".scion-taskforce/prompt.md" should contain "Default Scion Task Force Prompt Template"

  Scenario: Init wizard offers menus, validates input and saves Vertex AI project and region
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    When I run "printf '3\nclaude\nopencode\n\n2\nBad_Proj\nmy-proj-123\neu-central1\n4\n\n9\n1\ny\nn\n' | GOOGLE_CLOUD_PROJECT=tk-detected-proj ticket scion-taskforce init --interactive"
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
    When I run "printf '\n\n\n\ny\nn\n' | ticket scion-taskforce init --interactive"
    Then the command should succeed
    And the output should contain "recommended: API-key auth"
    And the output should contain "skipped; gemini-cli authenticates with the GEMINI_API_KEY Scion secret"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "api-key"
    And the file ".scion-taskforce/scion-taskforce.yaml" should contain "tk-worker-gemini-cli-with-api-key-auth"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/scion-agent.yaml" should contain "agent_instructions: agents.md"
    And the file ".scion/templates/tk-worker-gemini-cli-with-api-key-auth/agents.md" should contain "Commit on your ticket branch only"

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
    Then the output should contain "provider unavailable: scion list exited 125: Error: podman ps failed"
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
    And the fake scion prompt for "tf-0071" should contain "gh pr checkout 2246"
    And the fake scion prompt for "tf-0071" should contain "never approve/merge"
    And the fake scion prompt for "tf-0071" should not contain "Your Job: Implementation"
    And the fake scion prompt for "tf-0072" should contain "Your Job: Implementation"
    And the fake scion prompt for "tf-0072" should contain "tk` may NOT be installed in this pod"
    And the fake scion prompt for "tf-0072" should contain "tags: [taskforce, waiting-for-review]"
    And the fake scion prompt for "tf-0072" should contain "do NOT push, merge, rebase onto other branches, or `git stash`"

  Scenario: A custom worker.prompt_file template overrides the built-in brief
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And the scion-taskforce setting "worker.prompt_file" is ".tickets/worker-prompt.md"
    And a file ".tickets/worker-prompt.md" with content "CUSTOM BRIEF for {ticket_id} ({work_type}) on {branch}: {ticket_title}"
    And a ticket exists with ID "tf-0075" and title "Custom prompt ticket"
    And ticket "tf-0075" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch tf-0075"
    Then the command should succeed
    And the fake scion prompt for "tf-0075" should contain "CUSTOM BRIEF for tf-0075 (implement) on tf-0075: Custom prompt ticket"
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

  Scenario: Dispatch never links an unlinked project folder to the Scion Hub
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
    And ticket "tf-0201" should contain "started Scion worker `tf-0201` on branch `tf-0201`"
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
    Then ticket "tf-0232" should contain "`taskforce` tag removed; stopped and removed worker `tf-0232` (branch `tf-0232` kept)"
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
