Feature: Ticket IDs
  As several agents creating tickets on parallel branches
  I want long random ticket IDs
  So that IDs rarely collide when branches merge, while old IDs keep working

  Background:
    Given a clean tickets directory

  Scenario: New IDs use a 6-character hash by default
    When I run "ticket create 'Six chars'"
    Then the command should succeed
    And the output should match pattern "^[a-z0-9]+-[a-z0-9]{6}$"

  Scenario: TK_ID_HASH_LENGTH sets the hash length
    When I run "TK_ID_HASH_LENGTH=10 ticket create 'Ten chars'"
    Then the output should match pattern "^[a-z0-9]+-[a-z0-9]{10}$"

  Scenario: An out-of-range TK_ID_HASH_LENGTH falls back to 6
    When I run "TK_ID_HASH_LENGTH=2 ticket create 'Too short'"
    Then the output should match pattern "^[a-z0-9]+-[a-z0-9]{6}$"

  Scenario: Legacy 4-character IDs resolve exactly and by partial ID next to longer IDs
    Given a ticket exists with ID "abc-1x2y" and title "Legacy ticket"
    And a ticket exists with ID "abc-1x2y9z" and title "New ticket"
    When I run "ticket show abc-1x2y"
    Then the command should succeed
    And the output should contain "Legacy ticket"
    When I run "ticket show 1x2y9z"
    Then the output should contain "New ticket"
    When I run "ticket start abc-1x2y"
    Then ticket "abc-1x2y" should have field "status" with value "in_progress"
    And ticket "abc-1x2y9z" should have field "status" with value "open"
