Feature: Web UI tolerates odd ticket frontmatter
  As a Web UI user
  I want the board to load even when one ticket file is unusual or broken
  So that a single bad file never hides all my tickets

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "test-0001" and title "Healthy"
    And a ticket exists with ID "test-0002" and title "Imported PR"
    And ticket "test-0002" has raw frontmatter line "tags: [github-sync, pr#81, autorelease:pending, autorelease: pending]"

  Scenario: Flow-list tag that YAML reads as a mapping is kept as text
    Then the web UI should show ticket "test-0002" with tags "github-sync|pr#81|autorelease:pending|autorelease: pending"

  Scenario: API lists all tickets when one has such a tag
    When I send API GET "/api/tickets?directory={dir}"
    Then the API status should be 200
    And the API ticket list should contain ticket "test-0001"
    And the API ticket list should contain ticket "test-0002"

  Scenario: A ticket that fails to parse is skipped, not fatal
    Given the web UI parser fails on ticket "test-0002"
    Then the API ticket list should contain ticket "test-0001"
    And the API ticket list should not contain ticket "test-0002"
