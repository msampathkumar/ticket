Feature: Agent skill from an installed tk
  As a user who installed tk with ./install.sh (no repository beside it)
  I want tk agent-skill to print the current skill
  So that installed agents never get a stale copy

  Scenario: tk agent-skill from a copy outside the repository prints agent-skill/tk/SKILL.md
    Given a copy of the ticket script outside the repository at "bin/tk"
    When I run "bin/tk agent-skill"
    Then the command should succeed
    And the raw output should equal the repository agent skill

  Scenario: tk agent-skill --install from a copy outside the repository installs agent-skill/tk/SKILL.md
    Given a copy of the ticket script outside the repository at "bin/tk"
    When I run "AGENTS_SKILLS_DIR=$PWD/skills bin/tk agent-skill --install"
    Then the command should succeed
    And the file "skills/SKILL.md" should equal the repository agent skill
