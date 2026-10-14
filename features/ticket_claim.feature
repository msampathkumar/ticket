Feature: Atomic ticket claiming
  As one of several agents working in the same repository
  I want to claim a ticket atomically
  So that two agents never start the same ticket

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "claim-0001" and title "Shared task"

  Scenario: Two agents claim the same ticket concurrently and exactly one wins
    When 2 agents concurrently claim ticket "claim-0001"
    Then exactly one claim should succeed and the others should exit with code 3
    And ticket "claim-0001" should be assigned to the winning agent
    And the file ".tickets/.locks/claim-0001.lock" should not exist

  Scenario: Many agents race for one ticket
    When 8 agents concurrently claim ticket "claim-0001"
    Then exactly one claim should succeed and the others should exit with code 3
    And ticket "claim-0001" should be assigned to the winning agent

  Scenario: Claim sets status and assignee
    When I run "ticket start claim-0001 --claim --assignee alice"
    Then the command should succeed
    And the output should contain "Claimed claim-0001 -> in_progress (alice)"
    And ticket "claim-0001" should have field "status" with value "in_progress"
    And ticket "claim-0001" should have field "assignee" with value "alice"

  Scenario: Claiming a ticket in progress for another assignee fails with exit code 3
    When I run "ticket start claim-0001 --claim --assignee alice"
    And I run "ticket start claim-0001 --claim --assignee bob"
    Then the exit code should be 3
    And the output should contain "already claimed by 'alice'"
    And ticket "claim-0001" should have field "assignee" with value "alice"

  Scenario: Re-claiming your own ticket succeeds
    When I run "ticket start claim-0001 --claim --assignee alice"
    And I run "ticket start --claim claim-0001 -a alice"
    Then the command should succeed

  Scenario: Plain start stays backward compatible
    When I run "ticket start claim-0001 --claim --assignee alice"
    And I run "ticket start claim-0001"
    Then the command should succeed
    And the output should contain "Updated claim-0001 -> in_progress"
    And ticket "claim-0001" should have field "assignee" with value "alice"

  Scenario: A stale lock is recovered
    Given ticket "claim-0001" has a stale lock
    When I run "ticket start claim-0001 --claim --assignee alice"
    Then the command should succeed
    And the file ".tickets/.locks/claim-0001.lock" should not exist

  Scenario: A live lock makes status writes time out with exit code 4
    Given ticket "claim-0001" has a live lock
    When I run "TK_LOCK_TIMEOUT=1 ticket close claim-0001"
    Then the exit code should be 4
    And the output should contain "is locked by another tk process"
    And ticket "claim-0001" should have field "status" with value "open"
