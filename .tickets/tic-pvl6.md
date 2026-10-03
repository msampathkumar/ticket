---
id: tic-pvl6
status: closed
deps: []
links: []
created: 2026-10-03T15:48:19Z
type: task
priority: 2
assignee: Sampath Kumar
---
# fix: cicd tests are failing.

fix the faiing cicd tests.


## Notes

**2026-10-03T17:04:44Z**

Fixed CI/CD test failures:
1. Resolved BDD compound step execution in features/scion_taskforce_plugin.feature:259 by introducing dedicated subdirectory navigation steps and prepending ticket directory to PATH in test runner.
2. Configured tool.ruff in pyproject.toml and resolved formatting/import issues across tk_webui/.
3. Fixed ShellCheck warnings (SC2034, SC2140, SC2155) in ticket, scripts/publish-homebrew.sh, and scripts/publish-aur.sh.
4. Streamlined GitHub Actions test matrix in .github/workflows/test.yml and added ignore paths in lint.yml.
5. Verified all 153 BDD scenarios and ruff checks pass cleanly.
