# Contributing to tk

Thank you for your interest in contributing to `tk`! We welcome bug reports, feature proposals, documentation improvements, and pull requests.

---

## Architecture & Philosophy

1. **Zero Mandatory Dependencies for Core**: The core `ticket` executable must remain a single portable Bash script (Bash 3.2+; Bash, not POSIX `sh`) using standard Unix tools (`awk`, `sed`). No runtime dependencies (Python, Node, Go) are required; `jq` is optional, only for `tk query <filter>`. See the [SPEC Non-goals](docs/SPEC.md#non-goals).
2. **Decoupled, Optional Plugins**: Extended functionality (the interactive Web UI, GitHub import, SCION Task Force agent dispatch) resides in modular plugins under `plugins/<name>/`, discovered via `$PATH` and listed automatically by `tk help`. The core script must never depend on, import, or special-case a plugin. All plugins are optional. The default `--full` bundle adds the Web UI; every other plugin is installed only on request (`./install.sh --<plugin>` or `--all`).
3. **Spec-Driven**: Feature changes must follow and update the relevant specification: `docs/SPEC.md` (core), `docs/PLUGIN_SPEC.md` (plugin standard), and the plugin's own `<PLUGIN-NAME>-SPEC.md` (e.g. `tk_webui/WEBUI-SPEC.md`, `plugins/github/GITHUB-SPEC.md`, `plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md`).

---

## Local Development Setup

### 1. Clone & Install
```bash
git clone https://github.com/msampathkumar/ticket.git
cd ticket

# Install full development environment
./install.sh --all
```

### 2. Running BDD Acceptance Tests
All CLI behavior and features are verified using Python `behave` BDD test suites:
```bash
# Run all acceptance tests
make test
```

### 3. Running Web UI Locally
```bash
# Launch local Web UI server
./run.sh [optional-directory]
```

---

## Pull Request Process

1. **Fork and Branch**: Create a feature branch with a descriptive name (`feat/my-feature` or `fix/issue-description`).
2. **Follow Code Standards**:
   - Keep Bash scripts portable to Bash 3.2 and `shellcheck -S warning` clean (as in CI).
   - Use Python type hints and clean formatting (`ruff check`) for `tk_webui/`.
3. **Verify Tests**: Ensure all BDD test scenarios pass before submitting:
   ```bash
   make test
   ```
4. **Update Documentation**: Update `README.md`, `docs/SPEC.md`, or `tk_webui/WEBUI-SPEC.md` when introducing new commands or UI views.
5. **Open Pull Request**: Use the structured pull request template to describe your changes.

---

## Code of Conduct

Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all community interactions.
