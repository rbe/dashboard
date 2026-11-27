# The Node targets of a project: npm and node-tooling. A project includes
# this file after project.mk or sdlc.mk, from the installed skill, and
# does not keep a copy of the targets in its Makefile.
#
#     include .claude/skills/r-project-setup/project.mk
#     include .claude/skills/r-node/node.mk
#
# Node and npm run through $(NODE), which is Podman on this machine.
# A project that sets NODE, NODE_IMAGE, NODE_VERSION, or NODE_DEV_TOOLS
# before the include keeps its value.
#
# A new project, or a project with no Prettier and no ESLint yet, runs
#   make node-tooling
# once. It creates package.json, adds the dev tools, writes the config
# files, and formats the project. A file or a dependency that is
# already there stays as it is. NAME sets the package name and NODE_DEV_TOOLS
# the dev tools, for example: make node-tooling NAME=my-app
# A library names what it ships, so that make build packs nothing else:
#   make npm ARGS='pkg set exports=./src/index.js files[0]=src'
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef NODE_MK
NODE_MK := 1

NODE_MK_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
ifndef PYTHON
include $(NODE_MK_DIR)../r-project-setup/podman-python.mk
endif

NODE_VERSION ?= 24
NODE_IMAGE ?= docker.io/library/node:$(NODE_VERSION)-bookworm-slim
# The dev tools of node-tooling. NAME, the package name of a new project,
# comes from tools.mk: the repository name of the remote origin, else
# the directory name.
NODE_DEV_TOOLS ?= prettier eslint @eslint/js globals
NODE ?= podman run --rm $(PYTHON_USERNS) --user $(PYTHON_UID):$(PYTHON_GID) -e HOME=/tmp -e CI \
	-e NODE_V8_COVERAGE -e npm_config_cache=/tmp/npm-cache \
	-e npm_config_update_notifier=false -v "$(CURDIR)":/work:Z -w /work $(NODE_IMAGE)
# Host mode (TOOLS=host of podman-python.mk): node and npm run from PATH.
# It replaces a NODE that the project set before the include.
ifeq ($(TOOLS),host)
NODE = env npm_config_update_notifier=false
endif

.PHONY: npm
.PHONY: node-tooling

# help-group: Tools
npm: ## Run npm in Podman on this machine. Set ARGS.
	@set -eu; \
	if [ -z "$(ARGS)" ]; then printf '%s\n' "npm: set ARGS to the npm arguments." >&2; exit 1; fi
	$(NODE) npm $(ARGS)

# One target for the Node tooling, every step through Podman:
# 1. package.json (npm init, name, version, type=module) when missing
# 2. NODE_DEV_TOOLS as exact devDependencies, each one not yet there
# 3. .prettierignore and eslint.config.mjs from the r-node skill, and
#    .editorconfig from r-project-setup, each one when missing
# 4. node_modules/ and coverage/ in .gitignore, each line when missing
# 5. make format-fix, so make format passes from the first commit
# A file or a dependency already in the project stays as it is.
node-tooling: ## Set up package.json, Prettier, ESLint, and EditorConfig, then format
	@set -eu; \
	if [ ! -f package.json ]; then \
	  $(NODE) npm init -y; \
	  $(NODE) npm pkg set name=$(NAME) version=0.1.0 type=module; \
	  $(NODE) npm pkg delete main repository scripts; \
	fi; \
	missing=""; \
	for tool in $(NODE_DEV_TOOLS); do \
	  if ! grep -q "\"$$tool\":" package.json; then missing="$$missing $$tool"; fi; \
	done; \
	if [ -n "$$missing" ]; then $(NODE) npm install --save-dev --save-exact $$missing; \
	else echo "node-tooling: $(NODE_DEV_TOOLS) already in package.json"; fi; \
	if [ ! -f .prettierignore ]; then cp .claude/skills/r-node/templates/prettierignore .prettierignore; fi; \
	if [ ! -f eslint.config.mjs ]; then cp .claude/skills/r-node/templates/eslint.config.mjs eslint.config.mjs; fi; \
	if [ ! -f .editorconfig ]; then cp .claude/skills/r-project-setup/templates/editorconfig .editorconfig; fi; \
	touch .gitignore; \
	for line in node_modules/ coverage/; do \
	  if ! grep -qx "$$line" .gitignore; then printf '%s\n' "$$line" >> .gitignore; fi; \
	done; \
	$(MAKE) --no-print-directory format-fix

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
