---
id: tic-ew5j
status: closed
deps: []
links: []
created: 2026-09-25T11:00:01Z
type: task
priority: 1
assignee: Sampath Kumar
---
# new plugin: create a github plugin

This would be a CLI only plugin.

It should provide a git sync feature to sync with all open pull requests and create tasks. The new task can have suffix `-<gh>-<id>`. Add a tag `issue` or `pr` depending on the nature of the request.

The tool should give an option to sync only GitHub issues or PR or both. Also, the tool should be able to sync the tasks regularly. For instance, after a couple of days when I sync old PRs will be closed, new PR gets added, and the commands that I add will be only in the local.

Create this as an independent optional plugin that people can install or not install. By default let us not install. 

So, when creating a task it only needs to capture the task title, description and url of the request.

If you have any other additions or suggestions, I'm open to that.

Do also provide an option called unsync to remove these github tasks completedly.

use proper labels or tags for these github synced issues.

