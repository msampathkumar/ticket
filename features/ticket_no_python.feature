Feature: Core CLI without python3
  As a user on a minimal system
  I want tk init, create and update to work with only Bash, awk and sed
  So that the core CLI has no python3 runtime dependency

  Background:
    Given a clean tickets directory
    And python3 is not available on PATH

  Scenario: init, create, update and show work without python3
    When I run "ticket init"
    Then the command should succeed
    And the global projects registry should be "."
    When I run "ticket create 'Created without python'"
    Then the command should succeed
    Given a ticket exists with ID "np-0001" and title "Original title"
    When I run "ticket update np-0001 -d 'Old desc'"
    And I run "ticket add-note np-0001 'keep this note'"
    And I run "ticket update np-0001 --title 'New title' -d 'Line one\\path' --design 'Use awk' --acceptance '- [ ] works'"
    Then the command should succeed
    When I run "ticket show np-0001"
    Then the output should contain "# New title"
    And the output should contain "Line one\\path"
    And the output should contain "## Design"
    And the output should contain "Use awk"
    And the output should contain "## Acceptance Criteria"
    And the output should contain "keep this note"
    And the output should not contain "Old desc"
    And python3 should not have been invoked

  Scenario: init keeps known projects, moves the current one first, and accepts the legacy list format
    Given the global projects registry contains ["/old/a", "/old/b"]
    When I run "ticket init"
    Then the command should succeed
    And the global projects registry should be ".,/old/a,/old/b"
    When I run "ticket init"
    Then the global projects registry should be ".,/old/a,/old/b"
    And python3 should not have been invoked
