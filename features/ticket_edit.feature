Feature: Ticket Edit
  As a user
  I want to edit tickets in my editor
  So that I can make complex changes easily

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "edit-0001" and title "Editable ticket"

  Scenario: Edit in non-TTY mode shows file path
    When I run "ticket edit edit-0001" in non-TTY mode
    Then the command should succeed
    And the output should contain "Edit ticket file:"
    And the output should contain ".tickets/edit-0001.md"

  Scenario: Edit non-existent ticket
    When I run "ticket edit nonexistent"
    Then the command should fail
    And the output should contain "Error: ticket 'nonexistent' not found"

  Scenario: Edit with partial ID
    When I run "ticket edit 0001" in non-TTY mode
    Then the command should succeed
    And the output should contain "edit-0001.md"

  Scenario: Updating a field that is absent from the frontmatter inserts it (portable on BSD and GNU sed)
    Given a clean tickets directory
    And a ticket exists with ID "edit-0002" and title "No tags yet"
    When I run "ticket update edit-0002 --tags github-sync,pr"
    Then the command should succeed
    And ticket "edit-0002" should have field "tags" with value "[github-sync, pr]"
    When I run "ticket update edit-0002 --tags github-sync,pr,taskforce"
    Then ticket "edit-0002" should have field "tags" with value "[github-sync, pr, taskforce]"
