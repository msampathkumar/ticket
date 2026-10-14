Feature: Web UI REST API
  As a Web UI user
  I want the local API to store and return ticket data safely
  So that the browser board reflects tk state without exposing the machine

  Background:
    Given a clean tickets directory

  Scenario: Create a ticket and list it
    When I send API POST "/api/tickets"
      """
      {"directory": "{dir}", "title": "API created ticket", "description": "Made over HTTP"}
      """
    Then the API status should be 200
    And the API field "ticket_id" should match "[a-z0-9]+-[a-z0-9]+"
    And the API ticket list should contain a ticket with title "API created ticket"

  Scenario: Request with a foreign Host header is rejected
    When I send API GET "/api/tickets?directory={dir}" with Host "evil.example"
    Then the API status should be 400

  Scenario: Cross-origin write is rejected
    When I send API POST "/api/tickets" from origin "http://evil.example"
      """
      {"directory": "{dir}", "title": "Should not exist"}
      """
    Then the API status should be 403
    And the tickets directory should contain 0 tickets

  Scenario: Same-origin write is accepted
    When I send API POST "/api/tickets" from origin "http://127.0.0.1"
      """
      {"directory": "{dir}", "title": "Same origin ticket"}
      """
    Then the API status should be 200

  Scenario: XSS payload is stored and returned as plain data
    When I send API POST "/api/tickets"
      """
      {"directory": "{dir}", "title": "<img src=x onerror=alert(1)>", "assignee": "<script>alert(2)</script>", "description": "<svg onload=alert(3)>"}
      """
    Then the API status should be 200
    And the API ticket list should contain a ticket with title "<img src=x onerror=alert(1)>"
    And the API ticket list should contain a ticket with assignee "<script>alert(2)</script>"
    And the API ticket list should contain a ticket with description "<svg onload=alert(3)>"
    And the API response should be JSON

  Scenario: Title that looks like an option is rejected
    When I send API POST "/api/tickets"
      """
      {"directory": "{dir}", "title": "--help"}
      """
    Then the API status should be 400
    And the API field "detail" should contain "must not start with '-'"
    And the tickets directory should contain 0 tickets

  Scenario: Config reports the CLI launch directory
    Given the web UI was launched for the scenario directory
    When I send API GET "/api/config"
    Then the API status should be 200
    And the API field "initial_dir" should be the scenario directory

  Scenario: Config reports no directory without the CLI
    Given the web UI was launched without the CLI
    When I send API GET "/api/config"
    Then the API field "initial_dir" should be null

  Scenario: Tickets version fingerprint changes when a ticket is created
    When I remember the API tickets version
    Then the API status should be 200
    And the API field "version" should match "\d+-\d+-\d+"
    When I send API POST "/api/tickets"
      """
      {"directory": "{dir}", "title": "Bump the fingerprint"}
      """
    Then the API tickets version should have changed

  Scenario: Tickets version is null without a tickets directory
    Given the tickets directory does not exist
    When I send API GET "/api/tickets/version?directory={dir}"
    Then the API status should be 200
    And the API field "version" should be null

  Scenario: Web UI version has a single source
    Then the web UI version should match pyproject.toml and WEBUI-SPEC.md
