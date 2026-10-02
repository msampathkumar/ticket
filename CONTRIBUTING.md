# Contributing to tk

Thank you for your interest in contributing to `tk`! We welcome bug reports, feature proposals, documentation improvements, and pull requests.

---

## 🏗️ Architecture & Philosophy

1. **Zero Mandatory Dependencies for Core**: The core `ticket` executable must remain pure POSIX Bash using standard Unix tools (`awk`, `sed`). No runtime dependencies (Python, Node, Go) are required for base ticket tracking.
2. **Decoupled, Optional Plugins**: Extended functionality (the interactive Web UI, GitHub sync, SCION Task Force orchestration) resides in modular plugins under `plugins/<name>/`, discovered via `$PATH` and listed automatically by `tk help`. The core script must never depend on, import, or special-case a plugin. Optional plugins are installed only on request (`./install.sh --<plugin>` or `--all`), never by the default `--full` bundle.
3. **Spec-Driven**: Feature changes must follow and update the relevant specification: `docs/SPEC.md` (core), `docs/PLUGIN_SPEC.md` (plugin standard), and the plugin's own `<PLUGIN-NAME>-SPEC.md` (e.g. `tk_webui/WEBUI-SPEC.md`, `plugins/github/GITHUB-SPEC.md`, `plugins/scion-taskforce/SCION-TASKFORCE-SPEC.md`).

---

## 🛠️ Local Development Setup

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

## 📋 Pull Request Process

1. **Fork and Branch**: Create a feature branch with a descriptive name (`feat/my-feature` or `fix/issue-description`).
2. **Follow Code Standards**:
   - Keep Bash scripts POSIX compliant (`shellcheck` clean).
   - Use Python type hints and clean formatting (`ruff check`) for `tk_webui/`.
3. **Verify Tests**: Ensure all 125+ BDD test scenarios pass before submitting:
   ```bash
   make test
   ```
4. **Update Documentation**: Update `README.md`, `docs/SPEC.md`, or `tk_webui/WEBUI-SPEC.md` when introducing new commands or UI views.
5. **Open Pull Request**: Use the structured pull request template to describe your changes.

---

## 📜 Code of Conduct

Please review and adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) in all community interactions.
