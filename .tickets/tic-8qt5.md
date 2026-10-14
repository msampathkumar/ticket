---
id: tic-8qt5
status: closed
deps: []
links: []
created: 2026-10-05T17:20:58Z
type: feature
priority: 2
assignee: scion-agent
---
# Make page layout expandable on larger screens

As of today, the ticket tool is working fantastic. However, when I have a larger screen, the page does not expand. There are a lot of unnecessary spaces on the left and right side of the panel giving it like a page that is at the center of the entire web page.


## Notes

**2026-10-14T19:49:37Z**

Plan: all four views, header and stats bar are capped at max-w-[1700px] in index.html (no width set in app.js). Remove the cap so content fills the viewport, keep existing px-4/sm:px-6/lg:px-8 padding and add 2xl:px-12. Widen timeline column from max-w-4xl on 2xl. No wide-layout toggle (would need app.js). Verify with headless Chrome screenshots at 768/1280/1920/2560 in all views.

**2026-10-14T19:55:10Z**

PR opened: https://github.com/msampathkumar/ticket/pull/18. index.html only; removed 1700px caps, added 2xl:px-12, timeline 2xl:max-w-6xl. Screenshots at 768/1280/1920/2560 for all views: 768 and 1280 unchanged, 1920/2560 now full width. make test 227 passed, ruff passed. No toggle (needs app.js).

**2026-10-14T19:57:07Z**

Coordinator: reviewed (screenshots 768-2560) and squash-merged PR #18. CI green. Removed 1700px cap, 2xl:px-12 padding, wider timeline column. Minor: table title cell max-w-xs truncate in app.js.
