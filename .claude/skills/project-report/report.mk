# The project report target. project.mk and sdlc.mk include this file
# when the skill is installed. Python runs through $(PYTHON), which is
# Podman on this machine.
#
#   make project-report
#
# PROJECT_REPORT_CMD is set here when the project did not set it.
# This file owns the target for both includes.

ifndef PROJECT_REPORT_MK
PROJECT_REPORT_MK := 1

PROJECT_REPORT_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

# Alone, as `make -f <this file> project-report`, no makefile has
# defined $(PYTHON) yet.
ifndef PYTHON
include $(PROJECT_REPORT_DIR)../project-setup/podman-python.mk
endif

ifeq ($(strip $(PROJECT_REPORT_CMD)),)
PROJECT_REPORT_CMD = $(PYTHON) "$(PROJECT_REPORT_DIR)scripts/project_report.py"
endif

.PHONY: project-report

# Generated. Hand-editing build/project-report.md is a defect.
project-report: ## Write the requirements map and the reviews
	mkdir -p build
	rm -f build/project-report.md
	$(PROJECT_REPORT_CMD) > build/project-report.md.tmp || { rm -f build/project-report.md.tmp; exit 1; }
	mv build/project-report.md.tmp build/project-report.md

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
