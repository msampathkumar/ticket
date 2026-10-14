Feature: Runtime files stay out of git
  As a user committing .tickets/ to git
  I want lock directories and the hook log ignored
  So that a commit during a tk write never captures runtime state

  Scenario: tk init writes .tickets/.gitignore and re-running it adds no duplicates
    When I run "ticket init"
    Then the command should succeed
    And the file ".tickets/.gitignore" should have the line ".locks/" 1 time(s)
    And the file ".tickets/.gitignore" should have the line ".hooks/hooks.log" 1 time(s)
    When I run "ticket init"
    Then the file ".tickets/.gitignore" should have the line ".locks/" 1 time(s)
    And the file ".tickets/.gitignore" should have the line ".hooks/hooks.log" 1 time(s)

  Scenario: tk init keeps an existing .tickets/.gitignore without a trailing newline
    Given a clean tickets directory
    When I run "printf '.scion-taskforce-logs' > .tickets/.gitignore"
    And I run "ticket init"
    Then the file ".tickets/.gitignore" should have the line ".scion-taskforce-logs" 1 time(s)
    And the file ".tickets/.gitignore" should have the line ".locks/" 1 time(s)

  Scenario: The lock directory ignores itself in repos initialized before this change
    Given a clean tickets directory
    And a ticket exists with ID "gi-0001" and title "Old repo"
    When I run "ticket start gi-0001"
    Then the command should succeed
    And the file ".tickets/.locks/.gitignore" should contain "*"
    And the file ".tickets/.gitignore" should not exist

  Scenario: Git does not see lock files
    Given a clean tickets directory
    And a ticket exists with ID "gi-0002" and title "Git check"
    And the project is a git repository
    When I run "ticket start gi-0002"
    And I run "mkdir -p .tickets/.locks/gi-0002.lock && touch .tickets/.locks/gi-0002.lock/owner && git status --porcelain --untracked-files=all .tickets"
    Then the output should not contain ".locks"
