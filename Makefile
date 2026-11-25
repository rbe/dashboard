# Node app delivered as a container image.
# Make contract: project-setup. help is the default goal. This makefile
# sets the command variables of the contract and defines none of the
# contract targets again. The GitHub makefile is the installed sdlc.mk of
# github-pipeline. It is included before any target and adds the contract
# targets, the image targets, version, publish tags, cleanup, and report.
#
# image, run, and stop need Podman and make only.
# They do not install Node or TypeScript on the host.
# Targets whose descriptions start with "Match CI" are the jobs the
# GitHub workflow runs. publish-container writes build/publish-version.txt.
# The workflow then runs cleanup-container-versions, which reads that file.
# Podman is the only container engine.

NAME ?= dashboard
OWNER ?= rbe
PORT ?= 4173
DEV_PORT ?= 5173
DATA_FILE ?= data/dashboard.md
DATA_ENV ?= DASHBOARD_FILE
API_PATH ?= /api/dashboard
SMOKE_NEEDLE ?= not for git

IMAGE_NAME ?= ghcr.io/$(OWNER)/$(NAME)
IMAGE ?= $(IMAGE_NAME)
PACKAGE ?= $(OWNER)/$(NAME)
KEEP_VERSIONS ?= 2
NODE_VERSION ?= 24
NODE_IMAGE ?= docker.io/library/node:$(NODE_VERSION)-bookworm-slim
CI_IMAGE ?= localhost/$(NAME):ci
# curl runs in this image for the smoke check of make build. It joins
# the network of the smoke container, so no port of the host is used.
CURL_IMAGE ?= docker.io/curlimages/curl:8.17.0

HELP_LEAD ?= Podman is the only container engine, on a laptop and in CI. Node $(NODE_VERSION) stays in the image. npm start is the Vite dev server on http://127.0.0.1:$(DEV_PORT). The data file is ./$(DATA_FILE).

NODE_RUN = podman run --rm -e HOME=/tmp -e CI -e npm_config_cache=/tmp/npm-cache \
	-e npm_config_update_notifier=false -v "$(CURDIR)":/work:Z -w /work $(NODE_IMAGE)
# The jobs after setup unpack the dependencies that setup packed.
NODE_DEPS = if [ ! -d node_modules ]; then \
	  if [ -f build/deps/node_modules.tar ]; then tar -xf build/deps/node_modules.tar; \
	  else $(NODE_RUN) npm ci; fi; \
	fi

# The command variables of the contract. A # inside one is written \#.
SETUP_CMD = set -eu; \
	mkdir -p build/deps build/summaries; \
	if [ ! -d node_modules ]; then $(NODE_RUN) npm ci; fi; \
	$(NODE_RUN) sh -c 'npm audit --audit-level=high || echo "npm audit reported advisories; continuing"'; \
	tar -cf build/deps/node_modules.tar node_modules; \
	printf '\# setup\n\nNode %s. Dependencies packed.\n' "$(NODE_VERSION)" > build/summaries/setup.md
# build makes and smokes the Linux binary, then image-ci of container.mk
# builds the image, runs SMOKE_CMD, and saves the image tar.
BUILD_CMD = set -eu; \
	$(NODE_DEPS); \
	$(NODE_RUN) npm run package:binary; \
	$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME); \
	$(THIS_MAKE) --no-print-directory image-ci
TEST_CMD = set -eu; \
	$(NODE_DEPS); \
	mkdir -p build/summaries build/test-results build/coverage; \
	$(NODE_RUN) npm test -- --coverage --reporter=default --reporter=json --outputFile.json=build/test-results/results.json; \
	printf '\# test\n\nnpm test with coverage.\n' > build/summaries/test.md
FORMAT_CMD = $(NODE_RUN) npm exec -- prettier --check .
FORMAT_FIX_CMD = $(NODE_RUN) npm exec -- prettier --write .
LINT_CMD = $(NODE_RUN) npm exec -- eslint .
# There is no integration entry. make test runs every test.
INTEGRATION_CMD = true
# Vitest writes lcov to build/coverage. Its workers write no V8 coverage,
# so there is no coverage map, and test-changed asks Vitest for the tests
# that import the changed files (ADR-0005).
COVERAGE_CMD = set -eu; \
	$(NODE_DEPS); \
	$(NODE_RUN) npm test -- --coverage; \
	base=$$(git merge-base HEAD origin/$(DEFAULT_BRANCH) 2>/dev/null || git merge-base HEAD $(DEFAULT_BRANCH) 2>/dev/null || git rev-parse -q --verify HEAD 2>/dev/null || git hash-object -t tree /dev/null); \
	git add -N .; \
	git diff "$$base" > build/coverage/change.diff; \
	REPORT=build/coverage/lcov.info $(DIFF_COVER)
TEST_CHANGED_CMD = set -eu; \
	$(NODE_DEPS); \
	changed=$$(grep -E '\.(ts|tsx|mjs|js)$$' build/coverage/changed.txt | while read -r f; do if [ -f "$$f" ]; then printf '%s ' "$$f"; fi; done); \
	if [ -z "$$changed" ]; then printf '%s\n' "test-changed: no changed source file. make test runs the full suite."; \
	else printf 'test-changed: vitest related %s\n' "$$changed"; $(NODE_RUN) npm exec -- vitest related --run $$changed; fi

RENDER_DOCS = 1
DOCS_CMD = set -eu; \
	mkdir -p build/docs build/summaries; \
	$(NODE_RUN) node scripts/render-docs.mjs --source docs --out build/docs
PUBLISH_IMAGE = 1
SDLC_JOBS ?= setup build test docs publish-container

# The image targets come from container.mk. The smoke check reads the
# API for the needle and the page for the React root.
IMAGE_BUILD_ARGS = --build-arg NODE_VERSION=$(NODE_VERSION) --label org.opencontainers.image.title="$(NAME)"
SMOKE_CMD = name=$(NAME)-smoke; \
	podman rm -f "$$name" >/dev/null 2>&1 || true; \
	podman run -d --name "$$name" -e PORT=$(PORT) "$(CI_IMAGE)" >/dev/null; \
	ok=0; \
	i=0; \
	while [ "$$i" -lt 30 ]; do \
	  if podman run --rm --network "container:$$name" $(CURL_IMAGE) -fsSk "https://127.0.0.1:$(PORT)$(API_PATH)" 2>/dev/null | grep -qF '$(SMOKE_NEEDLE)'; then ok=1; break; fi; \
	  i=$$((i + 1)); sleep 1; \
	done; \
	page=$$(podman run --rm --network "container:$$name" $(CURL_IMAGE) -fsSk "https://127.0.0.1:$(PORT)/" 2>/dev/null || true); \
	podman rm -f "$$name" >/dev/null 2>&1 || true; \
	test "$$ok" = 1; \
	printf '%s\n' "$$page" | grep -q 'id="root"'

include .claude/skills/github-pipeline/sdlc.mk

# Project targets.

.PHONY: run stop clean

run: image ## Run detached on https://127.0.0.1:PORT
	@mkdir -p data
	@podman rm -f $(NAME) >/dev/null 2>&1 || true
	podman run -d --name $(NAME) \
		-p 127.0.0.1:$(PORT):$(PORT) \
		-e PORT=$(PORT) \
		-e $(DATA_ENV)=/app/$(DATA_FILE) \
		-v "$(CURDIR)/data:/app/data:Z" \
		"$(IMAGE)"
	@echo "$(NAME) at https://127.0.0.1:$(PORT)"

stop: ## Stop the detached container
	@podman rm -f $(NAME) >/dev/null 2>&1 || true

clean: ## Remove build/, dist/, and node_modules/
	rm -rf build dist node_modules
