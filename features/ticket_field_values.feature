Feature: Frontmatter field values are stored verbatim
  As a user or agent setting assignees and references
  I want values with special characters stored exactly as given
  So that tk and YAML readers see the same value

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "fv-0001" and title "Field values"

  Scenario: Sed metacharacters in update values are stored verbatim
    When I run "ticket update fv-0001 -a 'a/b & c\d|e' --external-ref 'https://x.test/a?b=1&c=2' --tags 'x/y,z&w'"
    Then the command should succeed
    And ticket "fv-0001" should have field "assignee" with value "a/b & c\d|e"
    And ticket "fv-0001" should have field "external-ref" with value "https://x.test/a?b=1&c=2"
    And ticket "fv-0001" should have field "tags" with value "[x/y, z&w]"

  Scenario: Claim with an assignee containing a slash
    When I run "ticket start fv-0001 --claim --assignee 'team/agent-1'"
    Then the command should succeed
    And ticket "fv-0001" should have field "assignee" with value "team/agent-1"

  Scenario: Values that plain YAML would misread are single-quoted and read back unquoted
    When I run "ticket start fv-0001 --claim --assignee '@bot: one'"
    Then the command should succeed
    And ticket "fv-0001" should have field "assignee" with value "'@bot: one'"
    When I run "ticket start fv-0001 --claim --assignee '@bot: one'"
    Then the command should succeed
    When I run "ticket start fv-0001 --claim --assignee 'other'"
    Then the exit code should be 3
    And the output should contain "already claimed by '@bot: one'"

  Scenario: Newlines in single-line fields are rejected
    When I run "ticket update fv-0001 -a \"$(printf 'two\nlines')\""
    Then the command should fail
    And the output should contain "assignee must be a single line"
    When I run "ticket create 'New' --external-ref \"$(printf 'a\nb')\""
    Then the command should fail
    And the output should contain "external-ref must be a single line"

  Scenario: Only frontmatter fields are updated, not matching lines in the body
    When I run "printf '%b' '---\nid: fv-0002\nstatus: open\n---\n# Body test\n\nstatus: draft in body\n' > .tickets/fv-0002.md"
    And I run "ticket close fv-0002"
    Then the command should succeed
    And ticket "fv-0002" should contain "status: draft in body"
    And ticket "fv-0002" should have field "status" with value "closed"
