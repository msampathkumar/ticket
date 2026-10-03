Feature: SCION Task Force Plugin
  As a developer or autonomous orchestrator
  I want to manage a global SCION task force across projects
  So that tickets I opt in are claimed only after a verified worker launch, paused for review,
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

  Scenario: Multi-project registration and listing
    Given a clean tickets directory
    When I run "ticket scion-taskforce project add ."
    Then the command should succeed
    And the output should contain "Registered project with scion-taskforce"
    When I run "ticket scion-taskforce project list"
    Then the command should succeed
    And the output should contain "Registered projects (1):"
    When I run "ticket scion-taskforce project remove ."
    Then the command should succeed
    And the output should contain "Task force stopped for project"

  Scenario: Per-project stop unregisters the project and stops the daemon when none remain
    Given a clean tickets directory
    When I run "ticket scion-taskforce project add ."
    Then the command should succeed
    When I run "ticket scion-taskforce stop ."
    Then the command should succeed
    And the output should contain "Task force stopped for project"
    And the output should contain "No watched projects remain"
    When I run "ticket scion-taskforce project list"
    Then the output should contain "No projects registered"

  Scenario: Task force is opt-in - only tickets the user tagged taskforce are dispatched
    Given a clean tickets directory
    And a ticket exists with ID "tf-0001" and title "Opted-in task"
    And ticket "tf-0001" has tags "taskforce"
    And a ticket exists with ID "tf-0002" and title "Untagged task"
    And a ticket exists with ID "tf-0003" and title "Opted out task"
    And ticket "tf-0003" has tags "taskforce, no-taskforce"
    When I run "ticket scion-taskforce dispatch --dry-run"
    Then the command should succeed
    And the output should contain "spawned=1"
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
    When I run "ticket scion-taskforce dispatch"
    Then the command should succeed
    And the output should contain "spawned=0"
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
    When I run "ticket scion-taskforce watch --once"
    Then the command should succeed
    And the output should contain "spawned=2"
    And ticket "tf-0041" should have field "status" with value "in_progress"
    And ticket "tf-0042" should have field "status" with value "in_progress"
    And ticket "tf-0043" should have field "status" with value "open"
    And the fake scion runtime should have 2 pod(s)
    Given ticket "tf-0041" has tags "taskforce, waiting-for-review"
    When I run "ticket scion-taskforce watch --once"
    Then the command should succeed
    And the output should contain "paused=1"
    And the output should contain "spawned=1"
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
    When I run "ticket scion-taskforce watch --once --dry-run"
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
    When I run "ticket scion-taskforce dispatch"
    Then the command should succeed
    And the output should contain "spawned=2"
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

  Scenario: A worker whose pod dies without reporting back is flagged, noted on the ticket, and frees its slot
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a ticket exists with ID "tf-0081" and title "Will crash"
    And ticket "tf-0081" has tags "taskforce"
    And a ticket exists with ID "tf-0082" and title "Waiting for a slot"
    And ticket "tf-0082" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch"
    Then the command should succeed
    And the output should contain "spawned=1"
    And ticket "tf-0081" should have field "status" with value "in_progress"
    And ticket "tf-0082" should have field "status" with value "open"
    Given the fake scion pod "tf-0081" is in state "stopped"
    When I run "ticket scion-taskforce dispatch"
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
    When I run "ticket scion-taskforce dispatch"
    Then the output should contain "spawned=1"
    Given the fake scion pod "tf-0085" is in state "stopped"
    When I run "ticket scion-taskforce dispatch"
    Then the output should contain "lost=1"
    When I run "ticket reopen tf-0085"
    And I run "ticket scion-taskforce dispatch"
    Then the command should succeed
    And the output should contain "spawned=1"
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
    When I run "ticket scion-taskforce dispatch"
    Then the output should contain "spawned=1"
    When I run "ticket scion-taskforce logs"
    Then the output should contain "isolated workspace"
    Given I am in subdirectory ".scion/agents/tf-0090/workspace"
    When I run "ticket add-note tf-0090 'Worker report: diff is ready on branch tf-0090'"
    And I run "ticket update tf-0090 --tags taskforce,waiting-for-review"
    Then the command should succeed
    And ticket "tf-0090" should have field "status" with value "in_progress"
    Given I am back in the root directory
    When I run "ticket scion-taskforce dispatch"
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

  Scenario: Project-local worktree mode (.scion/) allows higher concurrent worker execution per project
    Given a clean tickets directory
    And a fake "scion" runtime in mode "ok"
    And a file ".scion/config" with content "simulated worktree project"
    And a ticket exists with ID "tf-0101" and title "W1" with priority 1
    And ticket "tf-0101" has tags "taskforce"
    And a ticket exists with ID "tf-0102" and title "W2" with priority 1
    And ticket "tf-0102" has tags "taskforce"
    And a ticket exists with ID "tf-0103" and title "W3" with priority 1
    And ticket "tf-0103" has tags "taskforce"
    When I run "ticket scion-taskforce dispatch"
    Then the command should succeed
    And the output should contain "spawned=3"
    And the fake scion runtime should have 3 pod(s)

