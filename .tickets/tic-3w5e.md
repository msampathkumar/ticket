---
id: tic-3w5e
status: closed
deps: []
links: []
created: 2026-10-03T14:17:21Z
type: task
priority: 2
assignee: Sampath Kumar
---
# agent skill command is not working

Logs
```
$ npx github:msampathkumar/ticket agent-skill --install
⠼
npm error code ENOENT
npm error syscall open
npm error path /Users/sampathm/.npm/_cacache/tmp/git-cloneDHgjDO/package.json
npm error errno -2
npm error enoent Could not read package.json: Error: ENOENT: no such file or directory, open '/Users/sampathm/.npm/_cacache/tmp/git-cloneDHgjDO/package.json'
npm error enoent This is related to npm not being able to find a file.
npm error enoent
npm error A complete log of this run can be found in: /Users/sampathm/.npm/_logs/2026-10-03T14_16_21_581Z-debug-0.log
```


## Notes

**2026-10-03T14:19:25Z**

Root package.json created. Verified locally with 'npx . agent-skill --install'. Once 'git push origin master' is executed, remote npx invocation will find package.json on GitHub.
