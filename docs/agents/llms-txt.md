---
title: LLM & Agent Context (llms.txt)
description: Machine-readable documentation standard for AI coding agents.
---

Following the [llms.txt](https://llmstxt.org/) standard, `ticket` provides machine-readable documentation endpoints at root:

- [`/llms.txt`](/llms.txt): Structured index linking to all markdown documentation files and guides with summaries.
- [`/llms-full.txt`](/llms-full.txt): Consolidated single-file reference combining all specifications and guides.

---

### How AI Agents Use `llms.txt`

When an AI coding assistant or agent operates in a repository or documentation site supporting `llms.txt`:
1. Fetch `/llms.txt` to discover the structure and markdown URLs of all guides and specs.
2. Fetch specific markdown files or `/llms-full.txt` to load documentation directly without web crawling or HTML scraping.
