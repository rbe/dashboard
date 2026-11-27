# Python runs in Podman on the machine where Make runs. The host does
# not need a Python install. Set PYTHON_IMAGE before the include to
# pick another version. A one-off command is `make py ARGS='...'`.
# PYTHONPATH holds /work/src, so a project with a src/ layout imports
# its package with no install step. An absent src/ does no harm.
# Use `=` for a command variable that calls $(PYTHON), so it expands
# after this file is included.

ifndef PODMAN_PYTHON_MK
PODMAN_PYTHON_MK := 1

PYTHON_IMAGE ?= docker.io/library/python:3.13-slim
PYTHON_UID := $(shell id -u)
PYTHON_GID := $(shell id -g)

# Rootless Podman on Linux maps --user to a sub-uid that cannot write the
# mounted tree. keep-id keeps the user of the host. On macOS and as root
# this stays empty.
PYTHON_USERNS := $(shell [ "$$(uname -s)" = Linux ] && [ "$$(podman info --format '{{.Host.Security.Rootless}}' 2>/dev/null)" = true ] && echo --userns=keep-id)

# TOOLS says where Make runs a tool. podman, the default, runs each tool
# in its image. host runs the same tool from the PATH of this machine,
# for a machine without Podman, such as a cloud session. tools.mk has the
# other tools of host mode and the target host-tools.
TOOLS ?= podman

ifeq ($(TOOLS),host)
PYTHON = env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$(CURDIR)/src" python3
else
PYTHON = podman run --rm $(PYTHON_USERNS) --user $(PYTHON_UID):$(PYTHON_GID) \
	-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/work/src \
	-v "$(CURDIR)":/work:Z -w /work \
	$(PYTHON_IMAGE) python3
endif

.PHONY: py

# help-group: Tools
py: ## Run Python in Podman on this machine. Set ARGS.
	@set -eu; \
	if [ -z "$(ARGS)" ]; then printf '%s\n' "py: set ARGS to the Python arguments." >&2; exit 1; fi
	$(PYTHON) $(ARGS)

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
