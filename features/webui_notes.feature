Feature: Web UI note parsing
  As a Web UI user
  I want notes split only at the timestamp lines tk add-note writes
  So that bold text inside a note does not break it apart

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "test-0001" and title "First"

  Scenario: Note containing a bold line is one note
    When I add a note to "test-0001" via the web UI with text
      """
      Summary of the review.
      **Important**
      Follow up next week.
      """
    Then the command should succeed
    And the web UI should show 1 note on "test-0001"
    And web UI note 1 should contain "**Important**"
    And web UI note 1 should contain "Follow up next week."

  Scenario: Separate notes are still split
    When I add note "first note" to "test-0001" via the web UI
    And I add note "second note" to "test-0001" via the web UI
    Then the web UI should show 2 notes on "test-0001"
    And web UI note 2 should contain "second note"
