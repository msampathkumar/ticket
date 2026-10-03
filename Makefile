.PHONY: test docs-dev docs-build docs-llms

test:
	uv run --with behave behave

docs-llms:
	./scripts/build_llms_full.sh

docs-dev: docs-llms
	uv run --with zensical zensical serve

docs-build: docs-llms
	uv run --with zensical zensical build
