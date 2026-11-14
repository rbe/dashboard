# Node app delivered as a container image.
# Set the product values, then include sdlc.mk before any target.
# sdlc.mk is the shared makefile. Copy it unchanged.
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
SMOKE_PORT ?= 18080

IMAGE_NAME ?= ghcr.io/$(OWNER)/$(NAME)
IMAGE ?= $(IMAGE_NAME)
PACKAGE ?= $(OWNER)/$(NAME)
KEEP_VERSIONS ?= 2
NODE_VERSION ?= 24
NODE_IMAGE ?= node:$(NODE_VERSION)-bookworm-slim
CI_IMAGE ?= localhost/$(NAME):ci

HELP_LEAD ?= Podman is the only container engine, on a laptop and in CI. Node $(NODE_VERSION) stays in the image. npm start is the Vite dev server on http://127.0.0.1:$(DEV_PORT). The data file is ./$(DATA_FILE).

include sdlc.mk

NODE_RUN = podman run --rm -e HOME=/tmp -e CI -e npm_config_cache=/tmp/npm-cache \
	-e npm_config_update_notifier=false -v "$(CURDIR)":/work:Z -w /work $(NODE_IMAGE)

.PHONY: deps npm-ci audit linux-binary smoke-linux-binary smoke-image login \
	_setup _build _test _docs _publish-container

setup: ## Match CI: npm ci, npm audit (a warning), pack node_modules
	@$(call SDLC_LOG,setup,_setup)

build: ## Match CI: Linux binary, one image, smoke, save the image tar
	@$(call SDLC_LOG,build,_build)

test: ## Match CI: tests, with results and coverage under build/
	@$(call SDLC_LOG,test,_test)

docs: ## Match CI: render docs/ to HTML under build/docs
	@$(call SDLC_LOG,docs,_docs)

login: ## Match CI: log in to ghcr.io with REGISTRY_USER and REGISTRY_TOKEN
	@set -eu; \
	test -n "$${REGISTRY_USER:-}" || { echo "login needs REGISTRY_USER" >&2; exit 1; }; \
	test -n "$${REGISTRY_TOKEN:-}" || { echo "login needs REGISTRY_TOKEN" >&2; exit 1; }; \
	printf '%s\n' "$$REGISTRY_TOKEN" | podman login ghcr.io --username "$$REGISTRY_USER" --password-stdin

publish-container: ## Match CI: push MAJOR.MINOR.PATCH-run and latest
	@$(call SDLC_LOG,publish-container,_publish-container)

npm-ci: ## npm ci inside the Node image
	$(NODE_RUN) npm ci

audit: ## npm audit (a warning, not a failure)
	$(NODE_RUN) sh -c 'npm audit --audit-level=high || echo "npm audit reported advisories; continuing"'

deps:
	@set -eu; \
	if [ -d node_modules ]; then \
	  echo "Using existing node_modules"; \
	elif [ -f build/deps/node_modules.tar ]; then \
	  tar -xf build/deps/node_modules.tar; \
	else \
	  $(THIS_MAKE) --no-print-directory npm-ci; \
	fi

linux-binary: deps ## Build the Linux binary
	$(NODE_RUN) npm run package:binary

smoke-linux-binary: linux-binary ## Smoke the Linux binary
	$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME)

image: ## Build the container image
	podman build -f Containerfile \
		--build-arg NODE_VERSION=$(NODE_VERSION) \
		--label org.opencontainers.image.source="https://github.com/$(PACKAGE)" \
		--label org.opencontainers.image.revision="$(or $(GITHUB_SHA),local)" \
		--label org.opencontainers.image.version="$(or $(GITHUB_RUN_NUMBER),local)" \
		--label org.opencontainers.image.title="$(NAME)" \
		-t "$(IMAGE)" -t "$(CI_IMAGE)" .

smoke-image: image ## Smoke the image on the API and the page root
	@set -eu; \
	command -v curl >/dev/null || { echo "smoke-image needs curl"; exit 1; }; \
	name='$(NAME)-smoke'; \
	podman rm -f "$$name" >/dev/null 2>&1 || true; \
	podman run -d --name "$$name" -p 127.0.0.1:$(SMOKE_PORT):$(PORT) -e PORT=$(PORT) "$(CI_IMAGE)" >/dev/null; \
	cleanup() { podman rm -f "$$name" >/dev/null 2>&1 || true; }; \
	trap cleanup EXIT; \
	ok=0; \
	i=0; \
	while [ "$$i" -lt 30 ]; do \
	  if curl -fsSk "https://127.0.0.1:$(SMOKE_PORT)$(API_PATH)" 2>/dev/null | grep -qF '$(SMOKE_NEEDLE)'; then ok=1; break; fi; \
	  i=$$((i + 1)); sleep 1; \
	done; \
	page=$$(curl -fsSk "https://127.0.0.1:$(SMOKE_PORT)/" || true); \
	test "$$ok" = 1; \
	printf '%s\n' "$$page" | grep -q 'id="root"'

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

_setup:
	@set -eu; \
	if [ ! -d node_modules ]; then $(THIS_MAKE) --no-print-directory npm-ci; fi; \
	$(THIS_MAKE) --no-print-directory audit; \
	mkdir -p build/deps; \
	tar -cf build/deps/node_modules.tar node_modules; \
	printf '# setup\n\nNode %s. Dependencies packed.\n' "$(NODE_VERSION)" > build/summaries/setup.md

_build:
	@set -eu; \
	$(THIS_MAKE) --no-print-directory linux-binary smoke-linux-binary smoke-image; \
	mkdir -p build/image; \
	podman save -o build/image/$(NAME)-image.tar "$(CI_IMAGE)"; \
	bytes=$$(wc -c < build/image/$(NAME)-image.tar | tr -d ' '); \
	printf '# build\n\nLinux binary: build/%s\nContainer image: %s\nImage archive: build/image/%s-image.tar (%s bytes)\n' \
	  "$(NAME)" "$(CI_IMAGE)" "$(NAME)" "$$bytes" > build/summaries/build.md

_test:
	@set -eu; \
	$(THIS_MAKE) --no-print-directory deps; \
	mkdir -p build/test-results build/coverage; \
	$(NODE_RUN) npm test -- --coverage --reporter=default --reporter=json --outputFile.json=build/test-results/results.json; \
	printf '# test\n\nnpm test with coverage.\n' > build/summaries/test.md

_docs:
	@set -eu; \
	mkdir -p build/docs build/summaries; \
	$(NODE_RUN) node scripts/render-docs.mjs --source docs --out build/docs

_publish-container:
	@set -eu; \
	if ! podman image inspect "$(CI_IMAGE)" >/dev/null 2>&1; then \
	  test -f build/image/$(NAME)-image.tar; \
	  podman load -i build/image/$(NAME)-image.tar; \
	fi; \
	version=$$($(THIS_MAKE) -s --no-print-directory version); \
	mkdir -p build; \
	printf '%s\n' "$$version" > build/publish-version.txt; \
	for tag in "$$version" latest; do \
	  podman tag "$(CI_IMAGE)" "$(IMAGE):$$tag"; \
	  podman push "$(IMAGE):$$tag"; \
	done; \
	printf '# publish-container\n\nStatus: pushed\nImage: %s\nTags:\n- %s\n- latest\n' "$(IMAGE)" "$$version" > build/summaries/publish-container.md
