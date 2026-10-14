Feature: GitHub import argument safety
  As a user importing GitHub issues
  I want attacker-controlled titles, bodies and labels stored as data
  So that none of them is parsed as a tk option

  Background:
    Given a clean tickets directory
    And a ticket exists with ID "seed-0001" and title "Existing ticket"

  Scenario: Option-like titles are stored verbatim
    Given a fake gh CLI that returns these issues:
      """
      [
        {"number": 1, "title": "--help", "body": "", "url": "https://github.com/o/r/issues/1", "state": "OPEN", "labels": []},
        {"number": 2, "title": "-d x", "body": "", "url": "https://github.com/o/r/issues/2", "state": "OPEN", "labels": []},
        {"number": 3, "title": "-p 0 urgent", "body": "", "url": "https://github.com/o/r/issues/3", "state": "OPEN", "labels": []}
      ]
      """
    When I run "ticket github sync --issues"
    Then the command should succeed
    And the output should contain "3 created"
    And the ticket imported from "gh-issue-1" should have title "--help"
    And the ticket imported from "gh-issue-2" should have title "-d x"
    And the ticket imported from "gh-issue-3" should have title "-p 0 urgent"
    And the ticket imported from "gh-issue-3" should have field "priority" with value "2"

  Scenario: Option-like body and unsafe labels are passed safely
    Given a fake gh CLI that returns these issues:
      """
      [
        {"number": 4, "title": "Normal title", "body": "--tags evil", "url": "https://github.com/o/r/issues/4", "state": "OPEN",
         "labels": [{"name": "a,b"}, {"name": "--parent"}, {"name": "x/y&z"}, {"name": "good first issue"}]}
      ]
      """
    When I run "ticket github sync --issues"
    Then the command should succeed
    And the ticket imported from "gh-issue-4" should have title "Normal title"
    And the ticket imported from "gh-issue-4" should contain "--tags evil"
    And the ticket imported from "gh-issue-4" should have field "tags" with value "[github-sync, github, issue, issue#4, a-b, parent, x-y-z, good-first-issue]"
    When I run "ticket github sync --issues"
    Then the command should succeed
    And the output should contain "0 created, 0 closed, 0 re-tagged, 1 up to date"
