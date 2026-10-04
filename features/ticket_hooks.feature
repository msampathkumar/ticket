Feature: Post-write hooks
  As a plugin author
  I want tk to run project hooks after every successful ticket write
  So that integrations react to saves instead of polling

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "hk-0001" and title "Hooked ticket"
    And a post-write hook that records events

  Scenario: Write commands fire the hook with the event, full ID and file
    When I run "ticket update 0001 --tags taskforce"
    And I run "ticket add-note hk-0001 'hello'"
    And I run "ticket start hk-0001"
    And I run "ticket close hk-0001"
    Then the hook log should contain "update hk-0001 depth=1 file=hk-0001.md"
    And the hook log should contain "add-note hk-0001"
    And the hook log should contain "start hk-0001"
    And the hook log should contain "close hk-0001"

  Scenario: Creating a ticket fires the hook with the new ID
    When I run "ticket create 'Brand new'"
    Then the command should succeed
    And the hook log should contain "create "

  Scenario: Read-only commands do not fire the hook
    When I run "ticket show hk-0001"
    And I run "ticket ls"
    And I run "ticket dep tree hk-0001"
    And I run "ticket ready"
    Then the hook log should be empty

  Scenario: Failed writes do not fire the hook
    When I run "ticket close nope-9999"
    Then the command should fail
    And the hook log should be empty

  Scenario: Nested calls from inside a hook do not fire hooks again
    Given the environment variable "TK_HOOK_DEPTH" is "1"
    When I run "ticket add-note hk-0001 'from a hook'"
    Then the command should succeed
    And the hook log should be empty

  Scenario: TK_NO_HOOKS disables hooks for one call
    Given the environment variable "TK_NO_HOOKS" is "1"
    When I run "ticket start hk-0001"
    Then the command should succeed
    And the hook log should be empty
