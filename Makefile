# Build and run the dashboard with Podman.
#
# build, run, and stop need Podman and make only.
# They do not install Node or TypeScript on the host.
#
# Targets whose descriptions start with "Match CI" are the steps the
# GitHub workflows run. Podman is the only container engine.
#
# Host checks and the image build run through Podman, so macOS and Linux
# run the same Linux steps. Node 24 stays in the image.
# macos-binary is the release job that codesigns on macOS. It uses Node 24
# already on PATH and does not install Node.

SHELL := /bin/bash

IMAGE ?= localhost/dashboard:latest
CI_IMAGE ?= localhost/dashboard:ci
NAME ?= dashboard
PORT ?= 4173
NODE_VERSION ?= 24
NODE_IMAGE ?= node:$(NODE_VERSION)-bookworm-slim
IMAGE_NAME ?= ghcr.io/rbe/dashboard
SMOKE_NAME ?= dashboard-ci
SMOKE_PORT ?= 4173
IMAGE_TAR ?= image/dashboard-image.tar
RELEASE_DIR ?= release

IMAGE_SOURCE ?= $(if $(GITHUB_SERVER_URL),$(GITHUB_SERVER_URL)/$(GITHUB_REPOSITORY),https://github.com/rbe/dashboard)
IMAGE_REVISION ?= $(or $(GITHUB_SHA),local)
IMAGE_VERSION ?= $(shell sed -n 's/^  "version": "\([^"]*\)".*/\1/p' package.json)

ifeq ($(shell command -v sha256sum >/dev/null 2>&1 && echo yes),yes)
SHA256 = sha256sum
else
SHA256 = shasum -a 256
endif

# Single line so the expanded command stays in one shell invocation.
NODE_RUN_OPTS = --rm -e HOME=/tmp -e npm_config_cache=/tmp/npm-cache -e npm_config_update_notifier=false -e NODE_VERSION="$(NODE_VERSION)" -e IMAGE_NAME="$(IMAGE_NAME)" -e GITHUB_REF -e GITHUB_REF_NAME -e GITHUB_SHA -e GITHUB_REPOSITORY -e GITHUB_SERVER_URL -e GITHUB_OUTPUT -e TGZ_NAME -e CI -v "$(CURDIR)":/work:Z -w /work
NODE_RUN = podman run $(NODE_RUN_OPTS) $(NODE_IMAGE)

.DEFAULT_GOAL := help
.PHONY: help build run stop ci host-checks check-tag npm-ci test linux-binary smoke-linux-binary pack-smoke image-tags ci-image image smoke-image macos-binary npm-tarball release-assets image-save image-load image-push npm-publish

help: ## Show this help
	@echo "Host requirements for build, run, and stop: Podman and make."
	@echo "Node.js and TypeScript are not installed on the host. Node $(NODE_VERSION) stays in the image."
	@echo
	@echo "Targets:"
	@grep -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'
	@echo
	@echo "Descriptions that start with \"Match CI\" are the steps the GitHub workflows run."
	@echo "Podman is the only container engine, on a laptop and in CI."
	@echo "make ci is a branch push: Linux host checks, then one image build and its smoke."
	@echo "make run is detached and listens on https://127.0.0.1:$(PORT)."
	@echo "The board file is ./data/dashboard.md (mounted into the container)."
	@echo "The self-signed certificate is ./data/tls/cert.pem."
	@echo "Override the port with: make run PORT=9000"

build: ## Build the local image
	podman build -f Containerfile --build-arg NODE_VERSION=$(NODE_VERSION) -t "$(IMAGE)" .

run: build ## Run the app detached (stop it with make stop)
	@podman rm -f $(NAME) >/dev/null 2>&1 || true
	podman run -d --name $(NAME) \
		-p 127.0.0.1:$(PORT):$(PORT) \
		-e PORT=$(PORT) \
		-e DASHBOARD_FILE=/app/data/dashboard.md \
		-v "$(CURDIR)/data:/app/data:Z" \
		"$(IMAGE)"
	@echo "Dashboard at https://127.0.0.1:$(PORT)"

stop: ## Stop and remove the detached container
	@podman rm -f $(NAME) >/dev/null 2>&1 || true
	@echo "Stopped $(NAME)"

ci: host-checks ci-image ## Match CI: Linux host checks, then one image build and smoke

host-checks: check-tag npm-ci test linux-binary smoke-linux-binary pack-smoke ## Match CI: npm ci, npm test, Linux binary, pack smoke

check-tag: ## Match CI: a v* tag matches package.json
	@set -euo pipefail; \
	ref="$${GITHUB_REF:-}"; \
	case "$$ref" in \
	  refs/tags/v*) ;; \
	  *) echo "Not a v* tag; package version check skipped"; exit 0 ;; \
	esac; \
	$(NODE_RUN) node -e 'const tag=String(process.env.GITHUB_REF_NAME||"").replace(/^v/,""); const pkg=require("./package.json").version; if(tag!==pkg){console.error("Tag v"+tag+" does not match package.json version "+pkg); process.exit(1)} console.log("Tag v"+tag+" matches package.json")'

npm-ci: ## Match CI: npm ci
	$(NODE_RUN) npm ci

test: npm-ci ## Match CI: npm test
	$(NODE_RUN) npm test

linux-binary: npm-ci ## Match CI: npm run package:binary
	$(NODE_RUN) npm run package:binary

smoke-linux-binary: linux-binary ## Match CI: smoke build/dashboard
	$(NODE_RUN) node scripts/smoke-binary.mjs build/dashboard

# package:binary already ran npm run build, and prepack would compile again.
# dist is listed in package.json "files".
pack-smoke: linux-binary ## Match CI: npm pack --ignore-scripts and smoke the CLI
	$(NODE_RUN) sh -eu -c 'stage=$$(mktemp -d); npm pack --ignore-scripts --pack-destination "$$stage"; tgz=$$(echo "$$stage"/dashboard-*.tgz); prefix="$$stage/prefix"; npm install -g "$$tgz" --prefix "$$prefix"; "$$prefix/bin/dashboard" --help; node scripts/smoke-binary.mjs "$$prefix/bin/dashboard"'

image-tags: ## Match CI: resolve tags with scripts/container-tags.mjs
	@set -euo pipefail; \
	extra=""; \
	if [ -n "$${GITHUB_OUTPUT:-}" ]; then \
	  extra="-v $${GITHUB_OUTPUT}:$${GITHUB_OUTPUT}"; \
	fi; \
	podman run $(NODE_RUN_OPTS) $$extra $(NODE_IMAGE) node scripts/container-tags.mjs

ci-image: smoke-image ## Match CI: build the image once, then smoke it

image: ## Match CI: build the CI image from the Containerfile
	podman build \
		-f Containerfile \
		--build-arg NODE_VERSION=$(NODE_VERSION) \
		--label org.opencontainers.image.source="$(IMAGE_SOURCE)" \
		--label org.opencontainers.image.revision="$(IMAGE_REVISION)" \
		--label org.opencontainers.image.version="$(IMAGE_VERSION)" \
		--label org.opencontainers.image.title=dashboard \
		-t "$(CI_IMAGE)" \
		.

smoke-image: image ## Match CI: smoke the image from that build (needs curl)
	@set -euo pipefail; \
	command -v curl >/dev/null || { echo "smoke-image needs curl"; exit 1; }; \
	name='$(SMOKE_NAME)'; \
	port='$(SMOKE_PORT)'; \
	image='$(CI_IMAGE)'; \
	podman rm -f "$$name" >/dev/null 2>&1 || true; \
	podman run -d --name "$$name" -p "127.0.0.1:$$port:4173" -e PORT=4173 "$$image"; \
	cleanup() { \
	  status=$$?; \
	  if [ "$$status" -ne 0 ]; then podman logs "$$name" || true; fi; \
	  podman rm -f "$$name" >/dev/null 2>&1 || true; \
	  exit "$$status"; \
	}; \
	trap cleanup EXIT; \
	ok=0; \
	for _ in $$(seq 1 30); do \
	  body=$$(curl -fsS -k "https://127.0.0.1:$$port/api/dashboard" || true); \
	  case "$$body" in \
	    *'not for git'*) ok=1; break ;; \
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

macos-binary: ## Match CI: Apple silicon binary (macOS only; Node 24 on PATH)
	@set -euo pipefail; \
	if [ "$$(uname -s)" != "Darwin" ]; then \
	  echo "macos-binary matches the macOS release job and runs on macOS."; \
	  exit 1; \
	fi; \
	if ! command -v npm >/dev/null || ! command -v node >/dev/null; then \
	  echo "macos-binary uses Node 24 already on PATH. It does not install Node."; \
	  exit 1; \
	fi; \
	major=$$(node -p 'process.versions.node.split(".")[0]'); \
	if [ "$$major" -lt 24 ]; then \
	  echo "macos-binary matches CI and needs Node 24 on PATH. It does not install Node."; \
	  exit 1; \
	fi; \
	npm ci; \
	npm run build; \
	node scripts/build-binary.mjs --macos; \
	archs=$$(lipo -archs build/dashboard-macos); \
	echo "$$archs"; \
	test "$$archs" = "arm64"; \
	file build/dashboard-macos; \
	node scripts/smoke-binary.mjs build/dashboard-macos

npm-tarball: ## Match CI: npm pack into build/ (prepack compiles)
	$(NODE_RUN) sh -eu -c 'npm ci && mkdir -p build && npm pack --pack-destination build'

release-assets: ## Match CI: write build/SHA256SUMS and build/notes.md
	@set -euo pipefail; \
	binary="$(RELEASE_DIR)/dashboard-macos/dashboard-macos"; \
	tgz=$$(echo "$(RELEASE_DIR)"/npm-tarball/dashboard-*.tgz); \
	test -f "$$binary"; \
	test -f "$$tgz"; \
	tgz_name=$$(basename "$$tgz"); \
	mkdir -p build; \
	sum() { $(SHA256) "$$1" | awk '{print $$1}'; }; \
	{ \
	  printf '%s  %s\n' "$$(sum "$$binary")" dashboard-macos; \
	  printf '%s  %s\n' "$$(sum "$$tgz")" "$$tgz_name"; \
	} > build/SHA256SUMS; \
	TGZ_NAME="$$tgz_name" $(NODE_RUN) node scripts/release-notes.mjs > build/notes.md; \
	test -s build/notes.md; \
	echo "Wrote build/SHA256SUMS and build/notes.md"

image-save: ## Match CI: save the CI image to dashboard-image.tar
	podman save -o dashboard-image.tar "$(CI_IMAGE)"

image-load: ## Match CI: load the saved image tar
	podman load -i "$(IMAGE_TAR)"

image-push: ## Match CI: push the resolved tags (refuses when TAGS is empty)
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

npm-publish: ## Match CI: npm publish (refuses unless NPM_PUBLISH=true)
	@set -euo pipefail; \
	if [ "$(NPM_PUBLISH)" != "true" ]; then \
	  echo "npm-publish is the CI npm job. It does not run locally."; \
	  exit 1; \
	fi; \
	npm ci; \
	npm publish --access public --provenance
