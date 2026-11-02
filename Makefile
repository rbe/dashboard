# Build and run the app with Podman.
#
# image, run, and stop need Podman and make only.
# They do not install Node or TypeScript on the host.
#
# Targets whose descriptions start with "Match CI" are the jobs the
# GitHub workflow runs. Each job calls the target with the same name.
# Podman is the only container engine.
#
# setup, build, and test run through Podman, so macOS and Linux run the
# same Linux steps. Node 24 stays in the image.

SHELL := /bin/bash

# Product. These values are the only intended difference between the
# dashboard and ernaehrung Makefiles. NAME is the package name and the
# GitHub repository name.
NAME ?= dashboard
PORT ?= 4173
DEV_PORT ?= 5173
DATA_FILE ?= data/dashboard.md
DATA_ENV ?= DASHBOARD_FILE
API_PATH ?= /api/dashboard
SMOKE_NEEDLE ?= not for git

IMAGE ?= localhost/$(NAME):latest
CI_IMAGE ?= localhost/$(NAME):ci
NODE_VERSION ?= 24
NODE_IMAGE ?= node:$(NODE_VERSION)-bookworm-slim
IMAGE_NAME ?= ghcr.io/rbe/$(NAME)
VERSION ?= $(shell sed -n 's/^  "version": "\([^"]*\)".*/\1/p' package.json)
SMOKE_NAME ?= $(NAME)-ci
SMOKE_PORT ?= $(PORT)
IMAGE_TAR ?= image/$(NAME)-image.tar
SETUP_TAR ?= ci-artifacts/node_modules.tar

IMAGE_SOURCE ?= $(if $(GITHUB_SERVER_URL),$(GITHUB_SERVER_URL)/$(GITHUB_REPOSITORY),https://github.com/rbe/$(NAME))
IMAGE_REVISION ?= $(or $(GITHUB_SHA),local)
IMAGE_VERSION ?= $(VERSION)

# Single line so the expanded command stays in one shell invocation.
NODE_RUN_OPTS = --rm -e HOME=/tmp -e npm_config_cache=/tmp/npm-cache -e npm_config_update_notifier=false -e NODE_VERSION="$(NODE_VERSION)" -e IMAGE_NAME="$(IMAGE_NAME)" -e GITHUB_REF -e GITHUB_REF_NAME -e GITHUB_SHA -e GITHUB_REPOSITORY -e GITHUB_SERVER_URL -e GITHUB_OUTPUT -e GITHUB_EVENT_NAME -e DISPATCH_JOB -e JOB_RESULT_SETUP -e JOB_RESULT_BUILD -e JOB_RESULT_TEST -e JOB_RESULT_DOCS -e JOB_RESULT_PUBLISH_IMAGE -e CI -v "$(CURDIR)":/work:Z -w /work
NODE_RUN = podman run $(NODE_RUN_OPTS) $(NODE_IMAGE)

.DEFAULT_GOAL := help
.PHONY: help image run stop ci host-checks setup deps check-tag npm-ci audit build test linux-binary smoke-linux-binary report docs resolve-ghcr-tags ci-image smoke-image image-save image-load image-push publish-container

help: ## Show this help
	@echo "Host requirements for image, run, and stop: Podman and make."
	@echo "Node.js and TypeScript are not installed on the host. Node $(NODE_VERSION) stays in the image."
	@echo "npm start is the Vite dev server on http://127.0.0.1:$(DEV_PORT)."
	@echo
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-24s %s\n", $$1, $$2}'
	@echo
	@echo "Descriptions that start with \"Match CI\" are the jobs the GitHub workflow runs."
	@echo "Podman is the only container engine, on a laptop and in CI."
	@echo "make ci runs setup, build, test, docs, and report. It does not publish."
	@echo "make run builds the image if needed and listens on https://127.0.0.1:$(PORT)."
	@echo "The data file is ./$(DATA_FILE) (mounted into the container)."
	@echo "The self-signed certificate is ./data/tls/cert.pem."
	@echo "Override the port with: make run PORT=9000"

image: ## Build the container image
	podman build \
		-f Containerfile \
		--build-arg NODE_VERSION=$(NODE_VERSION) \
		--label org.opencontainers.image.source="$(IMAGE_SOURCE)" \
		--label org.opencontainers.image.revision="$(IMAGE_REVISION)" \
		--label org.opencontainers.image.version="$(IMAGE_VERSION)" \
		--label org.opencontainers.image.title=$(NAME) \
		-t "$(IMAGE)" \
		-t "$(CI_IMAGE)" \
		.

run: image ## Run the app detached (stop it with make stop)
	@podman rm -f $(NAME) >/dev/null 2>&1 || true
	podman run -d --name $(NAME) \
		-p 127.0.0.1:$(PORT):$(PORT) \
		-e PORT=$(PORT) \
		-e $(DATA_ENV)=/app/$(DATA_FILE) \
		-v "$(CURDIR)/data:/app/data:Z" \
		"$(IMAGE)"
	@echo "$(NAME) at https://127.0.0.1:$(PORT)"

stop: ## Stop and remove the detached container
	@podman rm -f $(NAME) >/dev/null 2>&1 || true
	@echo "Stopped $(NAME)"

ci: setup build test docs report ## Laptop run through docs and report; this target does not publish
	@echo "Branch pipeline finished. Nothing was published."

# Local Linux checks. The workflow does not call this target.
host-checks: setup test linux-binary smoke-linux-binary

# CI entry targets log their make output. CI_LOG_INNER=1 is the real recipe.
# The workflow runs `make <job>` and uploads build/logs for the report.
ifneq ($(CI_LOG_INNER),)
setup: check-tag npm-ci audit
	@mkdir -p ci-artifacts build/summaries
	tar -cf $(SETUP_TAR) node_modules
	@{ \
	  echo "# setup"; \
	  echo; \
	  echo "node_modules archive: $(SETUP_TAR)"; \
	  echo "npm audit is a warning, not a failure. The log has the audit output."; \
	} > build/summaries/setup.md
else
setup: ## Match CI: install, version check, and npm audit
	@mkdir -p build/logs
	@set -o pipefail; $(MAKE) --no-print-directory CI_LOG_INNER=1 setup 2>&1 | tee build/logs/setup.log
endif

# Phony on purpose: the recipe reuses node_modules or the setup archive.
deps:
	@set -euo pipefail; \
	if [ -d node_modules ]; then \
	  echo "Using existing node_modules"; \
	else \
	  tarfile=""; \
	  for candidate in $(SETUP_TAR) ci-artifacts/ci-artifacts/node_modules.tar; do \
	    if [ -f "$$candidate" ]; then tarfile="$$candidate"; break; fi; \
	  done; \
	  if [ -n "$$tarfile" ]; then \
	    tar -xf "$$tarfile"; \
	  elif [ -d ci-artifacts ] && [ -n "$$(ls -A ci-artifacts 2>/dev/null || true)" ]; then \
	    echo "The setup archive is present but node_modules.tar was not found."; \
	    exit 1; \
	  else \
	    $(MAKE) npm-ci; \
	  fi; \
	fi

check-tag: ## A v* tag matches package.json
	@set -euo pipefail; \
	pkg=$$(sed -n 's/^  "version": "\([^"]*\)".*/\1/p' package.json); \
	if [ "$(VERSION)" != "$$pkg" ]; then \
	  echo "VERSION $(VERSION) does not match package.json $$pkg"; \
	  exit 1; \
	fi; \
	ref="$${GITHUB_REF:-}"; \
	case "$$ref" in \
	  refs/tags/v*) ;; \
	  *) echo "Not a v* tag; package version check skipped"; exit 0 ;; \
	esac; \
	$(NODE_RUN) node -e 'const tag=String(process.env.GITHUB_REF_NAME||"").replace(/^v/,""); const pkg=require("./package.json").version; if(tag!==pkg){console.error("Tag v"+tag+" does not match package.json version "+pkg); process.exit(1)} console.log("Tag v"+tag+" matches package.json")'

npm-ci: ## npm ci inside the Node image
	$(NODE_RUN) npm ci

audit: ## npm audit (a warning, not a failure)
	@if [ ! -d node_modules ]; then $(MAKE) npm-ci; fi
	$(NODE_RUN) sh -c 'npm audit --audit-level=high || echo "npm audit reported advisories; continuing"'

ifneq ($(CI_LOG_INNER),)
build: deps linux-binary smoke-linux-binary smoke-image image-save
	@mkdir -p build/summaries
	@bytes=$$(wc -c < $(NAME)-image.tar | tr -d ' '); \
	{ \
	  echo "# build"; \
	  echo; \
	  echo "Linux binary: build/$(NAME)"; \
	  echo "Container image: $(CI_IMAGE)"; \
	  echo "Node image: $(NODE_IMAGE)"; \
	  echo "Image archive: $(NAME)-image.tar ($$bytes bytes)"; \
	  echo "The archive is a job artifact for publish-container. It is not a GitHub release asset."; \
	} > build/summaries/build.md
	@echo "Built the Linux binary and $(CI_IMAGE)"
else
build: ## Match CI: Linux binary and one container image
	@mkdir -p build/logs
	@set -o pipefail; $(MAKE) --no-print-directory CI_LOG_INNER=1 build 2>&1 | tee build/logs/build.log
endif

ifneq ($(CI_LOG_INNER),)
test: deps
	$(NODE_RUN) sh -eu -c 'mkdir -p build && npm test -- --coverage --reporter=default --reporter=json --outputFile.json=build/test-results.json'
else
test: ## Match CI: coverage report and test output
	@mkdir -p build/logs
	@set -o pipefail; $(MAKE) --no-print-directory CI_LOG_INNER=1 test 2>&1 | tee build/logs/test.log
endif

linux-binary: deps ## Build the Linux binary
	$(NODE_RUN) npm run package:binary

smoke-linux-binary: linux-binary ## Smoke the Linux binary
	$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME)

ifneq ($(CI_LOG_INNER),)
docs:
	$(NODE_RUN) node scripts/render-docs.mjs
else
docs: ## Match CI: render docs/ to HTML; skip when none exist
	@mkdir -p build/logs
	@set -o pipefail; $(MAKE) --no-print-directory CI_LOG_INNER=1 docs 2>&1 | tee build/logs/docs.log
endif

resolve-ghcr-tags: ## Resolve GHCR tags from the git ref
	@set -euo pipefail; \
	extra=""; \
	if [ -n "$${GITHUB_OUTPUT:-}" ]; then \
	  extra="-v $${GITHUB_OUTPUT}:$${GITHUB_OUTPUT}"; \
	fi; \
	podman run $(NODE_RUN_OPTS) $$extra $(NODE_IMAGE) node scripts/container-tags.mjs

ci-image: smoke-image ## Build the image once, then smoke it

smoke-image: image ## Smoke the image from that build (needs curl)
	@set -euo pipefail; \
	command -v curl >/dev/null || { echo "smoke-image needs curl"; exit 1; }; \
	name='$(SMOKE_NAME)'; \
	port='$(SMOKE_PORT)'; \
	image='$(CI_IMAGE)'; \
	podman rm -f "$$name" >/dev/null 2>&1 || true; \
	podman run -d --name "$$name" -p "127.0.0.1:$$port:$(PORT)" -e PORT=$(PORT) "$$image"; \
	cleanup() { \
	  status=$$?; \
	  if [ "$$status" -ne 0 ]; then podman logs "$$name" || true; fi; \
	  podman rm -f "$$name" >/dev/null 2>&1 || true; \
	  exit "$$status"; \
	}; \
	trap cleanup EXIT; \
	ok=0; \
	for _ in $$(seq 1 30); do \
	  body=$$(curl -fsS -k "https://127.0.0.1:$$port$(API_PATH)" || true); \
	  case "$$body" in \
	    *'$(SMOKE_NEEDLE)'*) ok=1; break ;; \
	  esac; \
	  sleep 1; \
	done; \
	test "$$ok" = 1; \
	page=$$(curl -fsS -k "https://127.0.0.1:$$port/"); \
	case "$$page" in \
	  *'id="root"'*) ;; \
	  *) echo "index missing #root"; exit 1 ;; \
	esac; \
	echo "Image smoke passed for $$image"

image-save: ## Save the CI image tar
	podman save -o $(NAME)-image.tar "$(CI_IMAGE)"

image-load: ## Load the saved image tar
	podman load -i "$(IMAGE_TAR)"

image-push: ## Push the resolved GHCR tags (refuses when TAGS is empty)
	@set -euo pipefail; \
	tags="$(TAGS)"; \
	if [ -z "$$tags" ]; then \
	  echo "image-push publishes $(CI_IMAGE). CI sets TAGS. Refusing to push."; \
	  exit 1; \
	fi; \
	podman image inspect "$(CI_IMAGE)" >/dev/null; \
	set -f; \
	IFS=','; \
	set -- $$tags; \
	set +f; \
	count=0; \
	for tag in "$$@"; do \
	  [ -n "$$tag" ] || continue; \
	  podman tag "$(CI_IMAGE)" "$$tag"; \
	  podman push "$$tag"; \
	  count=$$((count + 1)); \
	done; \
	test "$$count" -gt 0

ifneq ($(CI_LOG_INNER),)
publish-container:
	@mkdir -p build/summaries
	@set -euo pipefail; \
	summary=build/summaries/publish-container.md; \
	image_name="$(IMAGE_NAME)"; \
	tags=""; \
	resolver=""; \
	status="failed"; \
	reason="publish-container did not finish."; \
	finish() { \
	  { \
	    echo "# publish-container"; \
	    echo; \
	    echo "Status: $$status"; \
	    echo "Image: $$image_name"; \
	    echo "Tags:"; \
	    if [ -n "$$tags" ]; then printf '%s\n' "$$tags" | tr ',' '\n' | sed 's/^/- /'; else echo "- none"; fi; \
	    echo "Reason: $$reason"; \
	    if [ -n "$$resolver" ]; then echo; echo "Resolver:"; printf '%s\n' "$$resolver"; fi; \
	  } > "$$summary"; \
	}; \
	trap finish EXIT; \
	if podman image inspect "$(CI_IMAGE)" >/dev/null 2>&1; then \
	  echo "Using image $(CI_IMAGE)"; \
	elif [ -f "$(IMAGE_TAR)" ]; then \
	  $(MAKE) image-load; \
	elif [ -f "image/image/$(NAME)-image.tar" ]; then \
	  mv "image/image/$(NAME)-image.tar" "$(IMAGE_TAR)"; \
	  $(MAKE) image-load; \
	elif [ "$${GITHUB_EVENT_NAME:-}" = "workflow_dispatch" ]; then \
	  $(MAKE) image; \
	else \
	  reason="Missing $(IMAGE_TAR). The build job produces it."; \
	  echo "$$reason"; \
	  exit 1; \
	fi; \
	resolver=$$($(MAKE) -s --no-print-directory resolve-ghcr-tags); \
	publish=$$(printf '%s\n' "$$resolver" | sed -n 's/^publish=//p'); \
	tags=$$(printf '%s\n' "$$resolver" | sed -n 's/^tags=//p'); \
	ref="$${GITHUB_REF:-}"; \
	event="$${GITHUB_EVENT_NAME:-}"; \
	reason="Resolved tags from $${ref:-unknown}."; \
	case "$$ref" in \
	  refs/tags/v*) reason="A v* tag that matches package.json publishes the version, major.minor, major, and latest tags." ;; \
	  refs/heads/master|refs/heads/main) reason="master or main publishes edge and sha-<commit>." ;; \
	  *) if [ "$$event" = "workflow_dispatch" ]; then reason="A manual publish-container publishes sha-<commit> from this ref."; fi ;; \
	esac; \
	if [ "$$publish" != "true" ]; then \
	  status="refused"; \
	  reason="Refusing to push. Resolved publish=$$publish. $$reason"; \
	  echo "$$reason"; \
	  exit 1; \
	fi; \
	TAGS="$$tags" $(MAKE) image-push; \
	status="pushed"
else
publish-container: ## Match CI: push the image saved by build
	@mkdir -p build/logs
	@set -o pipefail; $(MAKE) --no-print-directory CI_LOG_INNER=1 publish-container 2>&1 | tee build/logs/publish-container.log
endif

ifneq ($(CI_LOG_INNER),)
report:
	$(NODE_RUN) node scripts/assemble-report.mjs
	@if [ -n "$${GITHUB_STEP_SUMMARY:-}" ] && [ -f build/report/index.md ]; then cat build/report/index.md >> "$$GITHUB_STEP_SUMMARY"; fi
	@test -s build/report/index.md
	@echo "Wrote build/report/index.md"
else
report: ## Match CI: collect quality and process into one report
	@mkdir -p build/logs build/report/logs
	@set -o pipefail; $(MAKE) --no-print-directory CI_LOG_INNER=1 report 2>&1 | tee build/logs/report.log
	@cp build/logs/report.log build/report/logs/report.log
endif
