Feature: Web UI CLI argument safety
  As a Web UI user
  I want request values to reach tk as data
  So that a value starting with '-' is never parsed as a tk option

  Background:
    Given a clean tickets directory

  Scenario: Title starting with a dash is rejected
    When I create a ticket via the web UI with title "--help"
    Then the command should fail
    And the output should contain "must not start with '-'"
    And the tickets directory should contain 0 tickets

  Scenario: Option-like description is stored verbatim
    When I create a ticket via the web UI with title "Safe title" and description "--help"
    Then the command should succeed
    And the created ticket should contain "--help"

  Scenario: Option-like dependency ID is rejected
    Given a ticket exists with ID "test-0001" and title "First"
    When I add dependency "--help" to "test-0001" via the web UI
    Then the command should fail
    And the output should contain "Invalid dep_id"

  Scenario: Option-like note is stored verbatim
    Given a ticket exists with ID "test-0001" and title "First"
    When I add note "-p 1" to "test-0001" via the web UI
    Then the command should succeed
    And ticket "test-0001" should contain "-p 1"
