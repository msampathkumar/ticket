Feature: Non-ASCII project directory names
  As a user whose project folder name contains non-ASCII characters
  I want tk init and tk create to work without byte-sequence errors
  So that ticket files are written with valid ASCII IDs

  Scenario: tk init in a folder with non-ASCII characters writes the setup ticket with an ASCII prefix
    When I run "mkdir -p 'p ü3' && cd 'p ü3' && ticket init"
    Then the command should succeed
    And the output should not contain "Illegal byte sequence"
    When I run "ls 'p ü3/.tickets'"
    Then the output should match pattern "^p3-[a-z0-9]{6}\.md$"

  Scenario: An all non-ASCII folder name falls back to the "tk" prefix
    When I run "mkdir -p 'üöä/.tickets' && cd 'üöä' && ticket create 'Umlaut ticket'"
    Then the command should succeed
    And the output should not contain "Illegal byte sequence"
    And the output should match pattern "^tk-[a-z0-9]{6}$"
    When I run "ls üöä/.tickets"
    Then the output should match pattern "(?m)^tk-[a-z0-9]{6}\.md$"

  Scenario: A non-ASCII first letter does not produce a leading dash
    When I run "mkdir -p 'ü-proj/.tickets' && cd 'ü-proj' && ticket create 'Mixed'"
    Then the output should match pattern "^pro-[a-z0-9]{6}$"
