---
title: GitHub Sync
description: Bi-directional synchronization between local markdown tickets and GitHub issues and pull requests.
---

The optional GitHub plugin (`tk-github`) enables bi-directional synchronization between your local `.tickets/` markdown files and GitHub issues and pull requests.

---

### Features

- **Import GitHub Issues**: Pull GitHub issues directly into local markdown tickets with correct mapping of labels, assignees, and descriptions.
- **Push & Update**: Push local ticket updates to GitHub or sync status changes when PRs are merged or closed.
- **Clean Unsyncing**: Safely unlink and clean up external references without losing local history.

Install via:
```bash
./install.sh --github
```
