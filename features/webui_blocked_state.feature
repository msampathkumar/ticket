Feature: Web UI blocked and ready state
  As a Web UI user
  I want the Kanban lanes to agree with tk ready and tk blocked
  So that the browser and the CLI never disagree about actionable work

  Scenario: Web UI matches tk ready and tk blocked, including a missing dependency
    Given a clean tickets directory
    And a ticket exists with ID "test-0001" and title "Ready, no deps"
    And a ticket exists with ID "test-0002" and title "Missing dep"
    And ticket "test-0002" depends on "gone-9999"
    And a ticket exists with ID "test-0003" and title "Open dep"
    And ticket "test-0003" depends on "test-0001"
    And a ticket exists with ID "test-0004" and title "Closed with open dep"
    And ticket "test-0004" depends on "test-0001"
    And ticket "test-0004" has status "closed"
    And a ticket exists with ID "test-0005" and title "Closed dep"
    And ticket "test-0005" has status "closed"
    And a ticket exists with ID "test-0006" and title "In progress, dep closed"
    And ticket "test-0006" depends on "test-0005"
    And ticket "test-0006" has status "in_progress"
    Then the web UI ready and blocked tickets should match tk ready and tk blocked
    And the web UI ready tickets should be "test-0001,test-0006"
    And the web UI blocked tickets should be "test-0002,test-0003"
    And the web UI should show "test-0002" blocked by "gone-9999"
