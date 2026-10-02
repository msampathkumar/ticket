Feature: Modular installer keeps optional plugins optional
  As a user installing tk
  I want install.sh to install only what I ask for
  So that optional plugins never sneak into the default bundle and I can always see how to add them

  # --webui is deliberately not exercised here: it builds a Python venv.

  Scenario: --help lists every target and exits cleanly
    When I run the installer with "--help"
    Then the command should succeed
    And the output should contain "--core"
    And the output should contain "--webui"
    And the output should contain "--skill"
    And the output should contain "--github"
    And the output should contain "--scion-taskforce"
    And the output should contain "--full"
    And the output should contain "--all"
    And the installed executable "tk" should not exist

  Scenario: Unknown flags fail loudly instead of silently installing the default bundle
    When I run the installer with "--bogus"
    Then the command should fail
    And the output should contain "Unknown option: --bogus"
    And the installed executable "tk" should not exist

  Scenario: Core-only install does not pull in any plugin
    When I run the installer with "--core"
    Then the command should succeed
    And the installed executable "tk" should exist
    And the installed executable "ticket" should exist
    And the installed executable "tk-github" should not exist
    And the installed executable "tk-scion-taskforce" should not exist
    And the output should contain "Optional plugins not installed"
    And the output should contain "./install.sh --github"
    And the output should contain "./install.sh --scion-taskforce"

  Scenario: Flags accumulate so optional plugins can be added to any bundle
    When I run the installer with "--core --github --scion-taskforce"
    Then the command should succeed
    And the installed executable "tk" should exist
    And the installed executable "tk-github" should exist
    And the installed executable "ticket-github" should exist
    And the installed executable "tk-scion-taskforce" should exist
    And the installed executable "ticket-scion-taskforce" should exist
    And the output should contain "tk github sync"
    And the output should contain "tk scion-taskforce"
    And the output should not contain "Optional plugins not installed"

  Scenario: Installed plugins are auto-discovered by tk help with their one-line description
    When I run the installer with "--core --scion-taskforce"
    Then the command should succeed
    When I run "PATH=bin:$PATH bin/tk help"
    Then the command should succeed
    And the output should contain "scion-taskforce"
    And the output should contain "Autonomous SCION task force orchestrator"

  Scenario: The scion-taskforce target delegates to the plugin's own installer
    When I run the installer with "--scion-taskforce"
    Then the command should succeed
    And the output should contain "Installed standalone optional plugin"
    And the installed executable "tk-scion-taskforce" should exist
    And the installed executable "tk" should not exist
