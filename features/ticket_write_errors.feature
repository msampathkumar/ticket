Feature: Failed ticket file writes are reported
  As a user or agent scripting tk
  I want a write failure to exit non-zero with a clear error
  So that I never get a ticket ID for a file that does not exist

  Background:
    Given a clean tickets directory

  Scenario: create in a read-only tickets directory fails without printing an ID or firing hooks
    Given a post-write hook that records events
    When I run "chmod a-w .tickets && ticket create 'Lost ticket'; s=$?; chmod u+w .tickets; exit $s"
    Then the command should fail
    And the output should contain "Error: cannot write ticket file"
    And the output should not contain "Permission denied"
    And the output should not match a ticket ID pattern
    And the hook log should be empty

  Scenario: init with a read-only empty tickets directory fails without claiming success
    When I run "chmod a-w .tickets && HOME=$PWD/home ticket init; s=$?; chmod u+w .tickets; exit $s"
    Then the command should fail
    And the output should contain "Error: cannot write ticket file"
    And the output should not contain "Created initial setup ticket"

  Scenario: update of title and description fails when the file cannot be rewritten
    Given a ticket exists with ID "we-0001" and title "Original"
    When I run "chmod a-w .tickets && ticket update we-0001 --title 'Changed'; s=$?; chmod u+w .tickets; exit $s"
    Then the command should fail
    And the output should contain "Error: cannot write ticket file"
    And the output should not contain "Updated we-0001"
    And ticket "we-0001" should contain "# Original"

  Scenario: update of a file without frontmatter still leaves it unchanged and succeeds
    When I run "printf 'plain text\n' > .tickets/we-0002.md"
    And I run "ticket update we-0002 --title 'X'"
    Then the command should succeed
    And ticket "we-0002" should contain "plain text"
