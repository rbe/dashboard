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
# publish-npm runs on the host because npm provenance uses the runner token.

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
RELEASE_DIR ?= release
SETUP_TAR ?= ci-artifacts/node_modules.tar

IMAGE_SOURCE ?= $(if $(GITHUB_SERVER_URL),$(GITHUB_SERVER_URL)/$(GITHUB_REPOSITORY),https://github.com/rbe/$(NAME))
IMAGE_REVISION ?= $(or $(GITHUB_SHA),local)
IMAGE_VERSION ?= $(VERSION)

ifeq ($(shell command -v sha256sum >/dev/null 2>&1 && echo yes),yes)
SHA256 = sha256sum
else
SHA256 = shasum -a 256
endif

# Single line so the expanded command stays in one shell invocation.
NODE_RUN_OPTS = --rm -e HOME=/tmp -e npm_config_cache=/tmp/npm-cache -e npm_config_update_notifier=false -e NODE_VERSION="$(NODE_VERSION)" -e IMAGE_NAME="$(IMAGE_NAME)" -e GITHUB_REF -e GITHUB_REF_NAME -e GITHUB_SHA -e GITHUB_REPOSITORY -e GITHUB_SERVER_URL -e GITHUB_OUTPUT -e GITHUB_EVENT_NAME -e TGZ_NAME -e CI -v "$(CURDIR)":/work:Z -w /work
NODE_RUN = podman run $(NODE_RUN_OPTS) $(NODE_IMAGE)

.DEFAULT_GOAL := help
.PHONY: help image run stop ci host-checks setup deps check-tag npm-ci audit build test linux-binary smoke-linux-binary npm-package pack-smoke npm-tarball report docs resolve-ghcr-tags ci-image smoke-image image-save image-load image-push publish-container publish-npm npm-publish publish-github release-assets

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
	@echo "make ci is a branch push: setup, build, test, npm-package, report, and docs. It does not publish."
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

ci: setup build test npm-package report docs ## Match CI: branch push through report and docs, no publish
	@echo "Branch pipeline finished. Nothing was published."

# Local Linux checks. The workflow does not call this target.
host-checks: setup test linux-binary smoke-linux-binary npm-package

setup: check-tag npm-ci audit ## Match CI: install, version check, and npm audit
	@mkdir -p ci-artifacts
	tar -cf $(SETUP_TAR) node_modules

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

build: deps linux-binary smoke-linux-binary smoke-image image-save ## Match CI: Linux binary and one container image
	@echo "Built the Linux binary and $(CI_IMAGE)"

test: deps ## Match CI: coverage report and test output
	$(NODE_RUN) sh -eu -c 'mkdir -p build && npm test -- --coverage --reporter=default --reporter=json --outputFile.json=build/test-results.json'

linux-binary: deps ## Build the Linux binary
	$(NODE_RUN) npm run package:binary

smoke-linux-binary: linux-binary ## Smoke the Linux binary
	$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME)

# The build job uploads dist. Pack that tree. prepack would compile again,
# and a later job must not run npm run build.
# "build/name.tgz" is a GitHub shorthand to npm, so install and publish use "./".
# A leading ./ keeps the tarball a local file. The Node image then needs no git.
npm-package: deps ## Match CI: pack the npm tarball and smoke the packed CLI
	$(NODE_RUN) sh -eu -c 'if [ ! -f dist/index.html ]; then echo "npm-package needs dist from the build job. It does not compile the UI again."; exit 1; fi; mkdir -p build; npm pack --ignore-scripts --pack-destination build; tgz=$$(echo build/$(NAME)-*.tgz); test -f "$$tgz"; list=$$(mktemp); tar -tzf "$$tgz" > "$$list"; if ! grep -qx package/dist/index.html "$$list"; then echo "The packed app is missing dist/index.html."; exit 1; fi; rm -f "$$list"; stage=$$(mktemp -d); prefix="$$stage/prefix"; npm install -g "./$$tgz" --prefix "$$prefix"; "$$prefix/bin/$(NAME)" --help; node scripts/smoke-binary.mjs "$$prefix/bin/$(NAME)"'

pack-smoke: npm-package
npm-tarball: npm-package

report: ## Match CI: collect coverage and test output; skip when none exist
	@set -euo pipefail; \
	results=""; \
	coverage=""; \
	for candidate in build/test-results.json build/build/test-results.json; do \
	  if [ -f "$$candidate" ]; then results="$$candidate"; break; fi; \
	done; \
	for candidate in build/coverage build/build/coverage; do \
	  if [ -d "$$candidate" ]; then coverage="$$candidate"; break; fi; \
	done; \
	if [ -z "$$results" ] && [ -z "$$coverage" ]; then \
	  echo "No coverage report or test output. Skipping."; \
	  exit 0; \
	fi; \
	{ \
	  echo "# Test report"; \
	  echo; \
	  if [ -n "$$results" ]; then echo "Test output: $$results"; fi; \
	  if [ -n "$$coverage" ]; then echo "Coverage: $$coverage"; fi; \
	} > build/report.md; \
	test -s build/report.md; \
	if [ -n "$${GITHUB_STEP_SUMMARY:-}" ]; then cat build/report.md >> "$$GITHUB_STEP_SUMMARY"; fi; \
	echo "Wrote build/report.md"

docs: ## Match CI: render docs/ to HTML; skip when none exist
	$(NODE_RUN) node scripts/render-docs.mjs

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

publish-container: ## Match CI: push the image saved by build
	@set -euo pipefail; \
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
	  echo "Missing $(IMAGE_TAR). The build job produces it."; \
	  exit 1; \
	fi; \
	out=$$($(MAKE) -s --no-print-directory resolve-ghcr-tags); \
	publish=$$(printf '%s\n' "$$out" | sed -n 's/^publish=//p'); \
	tags=$$(printf '%s\n' "$$out" | sed -n 's/^tags=//p'); \
	if [ "$$publish" != "true" ]; then \
	  echo "Refusing to push. Resolved publish=$$publish"; \
	  exit 1; \
	fi; \
	TAGS="$$tags" $(MAKE) image-push

publish-npm: ## Match CI: publish the packed tarball (refuses unless NPM_PUBLISH=true)
	@set -euo pipefail; \
	if [ "$(NPM_PUBLISH)" != "true" ]; then \
	  echo "publish-npm refuses unless NPM_PUBLISH=true."; \
	  exit 1; \
	fi; \
	tgz=$$(echo build/$(NAME)-*.tgz); \
	if [ ! -f "$$tgz" ]; then \
	  echo "Missing npm tarball. npm-package produces it."; \
	  exit 1; \
	fi; \
	npm publish "./$$tgz" --access public --provenance

npm-publish: publish-npm

publish-github: ## Match CI: checksums and release notes for the GitHub release
	@set -euo pipefail; \
	mkdir -p "$(RELEASE_DIR)/npm-package" build; \
	tgz=""; \
	for candidate in \
	  "$(RELEASE_DIR)"/npm-package/$(NAME)-*.tgz \
	  build/$(NAME)-*.tgz \
	  "$(RELEASE_DIR)"/npm-package/build/$(NAME)-*.tgz; \
	do \
	  if [ -f "$$candidate" ]; then tgz="$$candidate"; break; fi; \
	done; \
	if [ -z "$$tgz" ]; then \
	  echo "publish-github needs the npm-package tarball. It does not pack again."; \
	  exit 1; \
	fi; \
	canon="$(RELEASE_DIR)/npm-package/$$(basename "$$tgz")"; \
	if [ "$$tgz" != "$$canon" ]; then cp "$$tgz" "$$canon"; fi; \
	tgz="$$canon"; \
	test -f "$$tgz"; \
	tgz_name=$$(basename "$$tgz"); \
	sum() { $(SHA256) "$$1" | awk '{print $$1}'; }; \
	printf '%s  %s\n' "$$(sum "$$tgz")" "$$tgz_name" > build/SHA256SUMS; \
	if [ "$$(uname -s)" = "Darwin" ]; then \
	  TGZ_NAME="$$tgz_name" node scripts/release-notes.mjs > build/notes.md; \
	else \
	  TGZ_NAME="$$tgz_name" $(NODE_RUN) node scripts/release-notes.mjs > build/notes.md; \
	fi; \
	test -s build/notes.md; \
	echo "Wrote build/SHA256SUMS and build/notes.md"

release-assets: publish-github
