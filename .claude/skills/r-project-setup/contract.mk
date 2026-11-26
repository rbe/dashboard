# The targets of the Make contract, from the command variables the
# project sets before the include. project.mk and the sdlc.mk of
# r-github-pipeline both include this file, so the targets are the same
# on either include. It does not define help.
#
# A project changes what these targets do only through the command
# variables. No project defines one of these targets again, and the
# Node and Gradle makefiles of r-github-pipeline set the variables too.
# A command variable that holds a # writes it as \#, because Make reads
# an unescaped # as a comment.
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef CONTRACT_MK
CONTRACT_MK := 1

REGISTRY ?= ghcr.io

.PHONY: setup build test project-report editorconfig format format-fix lint integration coverage

# The project stub. doctor.mk makes doctor the first prerequisite of
# setup. setup installs no tool on the host: every tool is a Podman
# image behind a target.
# help-group: Gates
setup: ## Resolve dependencies
ifeq ($(strip $(SETUP_CMD)),)
	@printf '%s\n' "setup: stub. Set SETUP_CMD before the include. Resolve this project's dependencies." >&2
	@exit 1
else
	$(SETUP_CMD)
endif

# Stub. The project sets BUILD_CMD. Empty fails the target.
build: ## Produce the artifact
ifeq ($(strip $(BUILD_CMD)),)
	@printf '%s\n' "build: stub. Set BUILD_CMD before the include. Produce this project's artifact." >&2
	@exit 1
else
	$(BUILD_CMD)
endif

# Stub. The project sets TEST_CMD. Empty fails the target.
# test is the unit tests. integration is the one integration entry.
test: ## Run the unit tests
ifeq ($(strip $(TEST_CMD)),)
	@printf '%s\n' "test: stub. Set TEST_CMD before the include. Run this project's unit tests." >&2
	@exit 1
else
	$(TEST_CMD)
endif

editorconfig: ## Check files against .editorconfig
	$(EDITORCONFIG)

format: ## Check the files with the one formatter
ifeq ($(strip $(FORMAT_CMD)),)
	@printf '%s\n' "format: stub. Set FORMAT_CMD before the include. One existing formatter." >&2
	@exit 1
else
	$(FORMAT_CMD)
endif

# format checks and changes nothing. format-fix rewrites the files.
format-fix: ## Rewrite the files with the one formatter
ifeq ($(strip $(FORMAT_FIX_CMD)),)
	@printf '%s\n' "format-fix: stub. Set FORMAT_FIX_CMD before the include. The formatter of format, in write mode." >&2
	@exit 1
else
	$(FORMAT_FIX_CMD)
endif

lint: ## Run the one linter
ifeq ($(strip $(LINT_CMD)),)
	@printf '%s\n' "lint: stub. Set LINT_CMD before the include. One existing linter." >&2
	@exit 1
else
	$(LINT_CMD)
endif

integration: ## Run the one integration entry
ifeq ($(strip $(INTEGRATION_CMD)),)
	@printf '%s\n' "integration: stub. Set INTEGRATION_CMD before the include. One integration entry." >&2
	@exit 1
else
	$(INTEGRATION_CMD)
endif

# COVERAGE_CMD writes build/coverage/diff.md. diff-cover is DIFF_COVER in tools.mk.
coverage: ## Report the lines this change touched
ifeq ($(strip $(COVERAGE_CMD)),)
	@printf '%s\n' "coverage: stub. Set COVERAGE_CMD before the include. Write build/coverage/diff.md for the lines this change touched." >&2
	@exit 1
else
	mkdir -p build/coverage
	rm -f build/coverage/diff.md
	$(COVERAGE_CMD)
endif

# test-changed is test-changed.mk beside this file. sdlc.mk includes it too.

# Generated. Hand-editing build/project-report.md is a defect.
# report.mk in the r-project-report skill owns this target when that skill
# is installed. This recipe is for a project without that include.
ifndef PROJECT_REPORT_MK
# help-group: Board
project-report: ## Write the requirements map and the reviews
ifeq ($(strip $(PROJECT_REPORT_CMD)),)
	@printf '%s\n' "project-report: stub. Set PROJECT_REPORT_CMD before the include. Write build/project-report.md." >&2
	@exit 1
else
	mkdir -p build
	rm -f build/project-report.md
	$(PROJECT_REPORT_CMD) > build/project-report.md.tmp || { rm -f build/project-report.md.tmp; exit 1; }
	mv build/project-report.md.tmp build/project-report.md
endif
endif

# Stub. Set RENDER_DOCS=1 only when this repository renders docs.
# Marker `# help-docs`: help lists this target only when RENDER_DOCS is 1.
ifeq ($(RENDER_DOCS),1)
# help-docs
.PHONY: docs
# help-group: Gates
docs: ## Render the docs
ifeq ($(strip $(DOCS_CMD)),)
	@printf '%s\n' "docs: stub. Set DOCS_CMD before the include. Run this project's renderer." >&2
	@exit 1
else
	$(DOCS_CMD)
endif
endif

# Real recipe. Set PUBLISH_IMAGE=1 only when an image is published.
# Marker `# help-login`: help lists this target only when PUBLISH_IMAGE is 1.
ifeq ($(PUBLISH_IMAGE),1)
# help-login
.PHONY: login
# help-group: Delivery
login: ## Log in to the registry
	@set -eu; \
	test -n "$(REGISTRY)" || { printf '%s\n' "login: set REGISTRY to the registry host." >&2; exit 1; }; \
	test -n "$${REGISTRY_USER:-}" || { printf '%s\n' "REGISTRY_USER is required" >&2; exit 1; }; \
	test -n "$${REGISTRY_TOKEN:-}" || { printf '%s\n' "REGISTRY_TOKEN is required" >&2; exit 1; }; \
	printf '%s\n' "$$REGISTRY_TOKEN" | podman login "$(REGISTRY)" --username "$$REGISTRY_USER" --password-stdin
endif

endif
