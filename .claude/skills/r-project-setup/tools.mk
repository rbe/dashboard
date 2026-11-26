# Existing tools. A project does not vendor a linter or a formatter.
# editorconfig-checker reads .editorconfig.
# diff-cover writes build/coverage/diff.md for the lines this change
# touched. The recipe sets REPORT to the Cobertura, JaCoCo, or lcov
# file. fail-under is 0: the report is the lines, not a percentage gate.
# Python runs in the image from podman-python.mk. Include that file first.

ifndef PROJECT_TOOLS_MK
PROJECT_TOOLS_MK := 1

EDITORCONFIG_IMAGE ?= ghcr.io/editorconfig-checker/editorconfig-checker:4.0.2
RUFF_IMAGE ?= ghcr.io/astral-sh/ruff:0.15.2
# The branch a slice is compared with. coverage and test-changed read it.
# Make finds it: the origin default branch, else main, else master.
ifndef DEFAULT_BRANCH
DEFAULT_BRANCH := $(or $(patsubst origin/%,%,$(shell git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null)),$(if $(shell git rev-parse -q --verify refs/heads/main 2>/dev/null),main,$(if $(shell git rev-parse -q --verify refs/heads/master 2>/dev/null),master,main)))
endif
# The name of the project: the repository name in the URL of the git
# remote origin, else the name of the directory. A language template, the
# image targets, and the tooling targets read it.
NAME ?= $(or $(shell git remote get-url origin 2>/dev/null | sed -n 's|.*github\.com[:/][^/]*/\([^/]*\)$$|\1|p' | sed 's|\.git$$||'),$(notdir $(CURDIR)))
COVERAGE_VERSION ?= 7.17.3
DIFF_COVER_VERSION ?= 11.0.2

EDITORCONFIG = podman run --rm -v "$(CURDIR)":/check:Z $(EDITORCONFIG_IMAGE)

# diff-cover needs git. This image has git and Python, so the recipe
# installs no system package.
DIFF_COVER_IMAGE ?= docker.io/library/python:3.13

DIFF_COVER = podman run --rm -e HOME=/tmp -e PYTHONDONTWRITEBYTECODE=1 -e REPORT $(PODMAN_NET_ARGS) -v "$(CURDIR)":/work:Z -w /work $(DIFF_COVER_IMAGE) sh -c 'set -eu; git config --global --add safe.directory /work; pip install --disable-pip-version-check --root-user-action=ignore -q --target /tmp/py "diff-cover==$(DIFF_COVER_VERSION)"; PYTHONPATH=/tmp/py python3 -m diff_cover.diff_cover_tool "$$REPORT" --diff-file build/coverage/change.diff --format markdown:build/coverage/diff.md --fail-under=0'

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

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
