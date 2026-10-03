---
title: LLM & Agent Context (llms.txt)
description: Machine-readable documentation standard for AI coding agents.
---

Inspired by [llmstxt.org](https://llmstxt.org/) and [Model Context Protocol](https://modelcontextprotocol.io), `ticket` provides dedicated machine-readable documentation endpoints at root:

- [`/llms.txt`](/llms.txt): Structured table of contents linking directly to all markdown documentation files and guides with summaries.
- [`/llms-full.txt`](/llms-full.txt): Consolidated single-file documentation reference combining all specifications and guides into a single context-window-friendly payload.

---

### How AI Agents Use `llms.txt`

When an AI coding assistant or agent visits a repository or documentation site supporting `llms.txt`:
1. It fetches `/llms.txt` to discover the exact structure and markdown URLs of all guides and specs.
2. It fetches specific markdown files or `/llms-full.txt` to instantly load complete technical context without web crawling or HTML scraping.
