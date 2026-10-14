.PHONY: test docs-dev docs-build docs-llms skill-sync skill-check

test:
	uv run --with behave behave

docs-llms:
	./scripts/build_llms_full.sh

docs-dev: docs-llms
	uvx zensical serve

docs-build: docs-llms
	uvx zensical build

# Embedded fallback skill in `ticket` (used by installed copies) must match agent-skill/tk/SKILL.md
skill-sync:
	./scripts/sync_skill.sh

skill-check:
	./scripts/sync_skill.sh --check
