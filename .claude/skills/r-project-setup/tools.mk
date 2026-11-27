# Existing tools. A project does not vendor a linter or a formatter.
# editorconfig-checker reads .editorconfig.
# diff-cover writes build/coverage/diff.md for the lines this change
# touched. The recipe sets REPORT to the Cobertura, JaCoCo, or lcov
# file. fail-under is 0: the report is the lines, not a percentage gate.
# Python runs in the image from podman-python.mk. Include that file first.

ifndef PROJECT_TOOLS_MK
PROJECT_TOOLS_MK := 1

# Use $(THIS_MAKE) in a recipe that must not run under `make -n`.
# A recipe that says $(MAKE) is executed even during a dry run. It is set
# here, before contract.mk, so a command variable of the project can use it.
THIS_MAKE := $(MAKE)

EDITORCONFIG_VERSION ?= 4.0.2
RUFF_VERSION ?= 0.15.2
EDITORCONFIG_IMAGE ?= ghcr.io/editorconfig-checker/editorconfig-checker:$(EDITORCONFIG_VERSION)
RUFF_IMAGE ?= ghcr.io/astral-sh/ruff:$(RUFF_VERSION)
# The branch a slice is compared with. coverage and test-changed read it.
# Make finds it: the origin default branch, else main, else master.
ifndef DEFAULT_BRANCH
DEFAULT_BRANCH := $(or $(patsubst origin/%,%,$(shell git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)),$(if $(shell git rev-parse -q --verify refs/heads/main 2>/dev/null),main,$(if $(shell git rev-parse -q --verify refs/heads/master 2>/dev/null),master,main)))
endif
# The name of the project: the repository name in the URL of the git
# remote origin, else the name of the directory. A language template, the
# image targets, and the tooling targets read it.
NAME ?= $(or $(shell git remote get-url origin 2>/dev/null | sed -n 's|.*github\.com[:/][^/]*/\([^/]*\)$$|\1|p' | sed 's|\.git$$||'),$(notdir $(CURDIR)))
# The board files: the files that the close of a task changes. A path
# that ends in / is a directory. The pre-push hook accepts a pushed commit
# that differs from build/gates.ok only in these files. ci-scope of
# r-github-pipeline reads the same list.
BOARD_FILES ?= docs/history/ docs/ROADMAP.md docs/proposals/
COVERAGE_VERSION ?= 7.17.3
DIFF_COVER_VERSION ?= 11.0.2

EDITORCONFIG = podman run --rm -v "$(CURDIR)":/check:Z $(EDITORCONFIG_IMAGE)

# diff-cover needs git. This image has git and Python, so the recipe
# installs no system package.
DIFF_COVER_IMAGE ?= docker.io/library/python:3.13

DIFF_COVER = podman run --rm -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e REPORT $(PODMAN_NET_ARGS) -v "$(CURDIR)":/work:Z -w /work $(DIFF_COVER_IMAGE) sh -c 'set -eu; git config --global --add safe.directory /work; pip install --disable-pip-version-check --root-user-action=ignore -q --target /tmp/py "diff-cover==$(DIFF_COVER_VERSION)"; PYTHONPATH=/tmp/py python3 -m diff_cover.diff_cover_tool "$$REPORT" --diff-file build/change.diff --format markdown:build/coverage/diff.md --fail-under=0'

# DIFF_BASE prints the commit that a change is measured against: the
# merge base with the default branch, else HEAD, else the empty tree.
DIFF_BASE = git merge-base HEAD origin/$(DEFAULT_BRANCH) 2>/dev/null || git merge-base HEAD $(DEFAULT_BRANCH) 2>/dev/null || git rev-parse -q --verify HEAD 2>/dev/null || git hash-object -t tree /dev/null

# CHANGE_DIFF writes build/change.diff, the file that DIFF_COVER
# reads: the diff against DIFF_BASE plus each untracked file that git does
# not ignore, outside build/. It stages nothing. The file stays outside
# build/coverage/, because a coverage tool may clean that directory.
# `git diff --no-index` exits 1 when the
# files differ, so only a status above 1 fails.
CHANGE_DIFF = set -eu; \
	mkdir -p build; \
	base=$$($(DIFF_BASE)); \
	git diff "$$base" > build/change.diff; \
	git ls-files --others --exclude-standard -- . ':!build/' | while IFS= read -r file; do \
	  status=0; git diff --no-index -- /dev/null "$$file" >> build/change.diff || status=$$?; \
	  [ "$$status" -le 1 ]; \
	done

# Extra podman arguments of a container that reads the network: the
# APM run of skills.mk, the GitHub CLI of sdlc.mk, and the pip runs of
# diff-cover and of the coverage recipe. Behind a proxy
# with its own CA, mount the CA file here.
PODMAN_NET_ARGS ?=

# APM installs and updates the skills. It runs in this image, which has
# git and Python, so the host needs no apm and no Python. skills.mk
# beside this file has the targets.
APM_IMAGE ?= docker.io/library/python:3.13
APM_VERSION ?= 0.36.1

APM = podman run --rm -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e GITHUB_APM_PAT -e GITHUB_TOKEN -e GH_TOKEN $(PODMAN_NET_ARGS) -v "$(CURDIR)":/work:Z -w /work $(APM_IMAGE) sh -c 'set -eu; git config --global --add safe.directory /work; pip install --disable-pip-version-check --root-user-action=ignore -q --target /tmp/py "apm-cli==$(APM_VERSION)"; PYTHONPATH=/tmp/py exec /tmp/py/bin/apm "$$@"' apm

# RUFF is the formatter and the linter of Python. COVERAGE_PYTHON runs a
# Python script with the package coverage, such as cover_tests.py of
# r-project-report. A command variable of a project uses them.
RUFF = podman run --rm -v "$(CURDIR)":/io:Z -w /io $(RUFF_IMAGE)
COVERAGE_PYTHON = podman run --rm -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 $(PODMAN_NET_ARGS) -v "$(CURDIR)":/work:Z -w /work $(PYTHON_IMAGE) sh -c 'set -eu; pip install --disable-pip-version-check --root-user-action=ignore -q --target /tmp/py "coverage==$(COVERAGE_VERSION)"; PYTHONPATH=/tmp/py exec python3 "$$@"' python3

# Host mode (TOOLS=host, see podman-python.mk). Each shared tool runs
# from the PATH of this machine, with build/host-tools/bin first. make
# host-tools installs the pinned versions there: ruff, coverage,
# diff-cover, and apm with pip into a venv, and editorconfig-checker with
# go install. The image targets (image, smoke, run, publish) still need
# Podman. A language skill sets its own tool for host mode.
HOST_TOOLS_DIR ?= $(CURDIR)/build/host-tools
ifeq ($(TOOLS),host)
export PATH := $(HOST_TOOLS_DIR)/bin:$(PATH)
EDITORCONFIG = editorconfig-checker
RUFF = ruff
COVERAGE_PYTHON = env PYTHONDONTWRITEBYTECODE=1 python3
DIFF_COVER = sh -c 'set -eu; diff-cover "$$REPORT" --diff-file build/change.diff --format markdown:build/coverage/diff.md --fail-under=0'
APM = apm
setup: host-tools
endif

.PHONY: host-tools

# help-group: Tools
host-tools: ## Install the pinned tools of host mode (TOOLS=host) into build/host-tools
	@set -eu; \
	command -v python3 >/dev/null 2>&1 || { printf '%s\n' "host-tools: python3 is not on PATH." >&2; exit 1; }; \
	command -v go >/dev/null 2>&1 || { printf '%s\n' "host-tools: go is not on PATH. editorconfig-checker needs it." >&2; exit 1; }; \
	[ -x "$(HOST_TOOLS_DIR)/bin/pip" ] || python3 -m venv "$(HOST_TOOLS_DIR)"; \
	"$(HOST_TOOLS_DIR)/bin/pip" install --disable-pip-version-check -q "ruff==$(RUFF_VERSION)" "coverage==$(COVERAGE_VERSION)" "diff-cover==$(DIFF_COVER_VERSION)" "apm-cli==$(APM_VERSION)"; \
	GOBIN="$(HOST_TOOLS_DIR)/bin" go install "github.com/editorconfig-checker/editorconfig-checker/v4/cmd/editorconfig-checker@v$(EDITORCONFIG_VERSION)"; \
	printf '%s\n' "host-tools: installed into $(HOST_TOOLS_DIR)"

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
