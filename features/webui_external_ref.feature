Feature: Web UI external reference
  As a Web UI user
  I want to see the external-ref that tk writes
  So that linked GitHub issues and other references show in the UI

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "test-0001" and title "First"

  Scenario: External ref written by tk is shown
    When I run "ticket update test-0001 --external-ref gh-issue-12"
    Then the command should succeed
    And the web UI should show external ref "gh-issue-12" on "test-0001"

  Scenario: External ref set in the Web UI round-trips
    When I set external ref "JIRA-456" on "test-0001" via the web UI
    Then ticket "test-0001" should contain "external-ref: JIRA-456"
    And the web UI should show external ref "JIRA-456" on "test-0001"

  Scenario: Legacy external_ref key is still read
    Given ticket "test-0001" has frontmatter line "external_ref: gh-7"
    Then the web UI should show external ref "gh-7" on "test-0001"
