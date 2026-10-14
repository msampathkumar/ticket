.PHONY: test docs-dev docs-build docs-llms skill-sync skill-check webui-css webui-css-check

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

# Prebuilt Web UI CSS must match tk_webui/static (pinned Tailwind CLI, see scripts/build-webui-css.sh)
webui-css:
	./scripts/build-webui-css.sh

webui-css-check: webui-css
	@git diff --exit-code tk_webui/static/css/tailwind.css || \
		{ echo "tk_webui/static/css/tailwind.css is stale: run 'make webui-css' and commit the result." >&2; exit 1; }
