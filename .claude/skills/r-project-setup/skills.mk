# The skills of the project are installed and updated with APM. APM
# runs in Podman: tools.mk beside this file pins APM_IMAGE and
# APM_VERSION. The host needs no apm. project.mk and the sdlc.mk of
# r-github-pipeline both include this file.
#
#   make skills-install
#   make skills-update DRY_RUN=1
#   make skills-update
#   make apm ARGS='install rbe/ralfskills --skill r-go'
#
# skills-install reads apm.yml and writes .claude/skills/ and
# apm.lock.yaml. skills-update takes the newer version that apm.yml
# allows. DRY_RUN=1 prints the plan and changes nothing. apm is a
# one-off APM command.
#
# A project whose Makefile has no include yet runs
#   make -f .claude/skills/r-project-setup/skills.mk skills-update
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef SKILLS_MK
SKILLS_MK := 1

SKILLS_MK_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(SKILLS_MK_DIR)tools.mk

.PHONY: skills-install skills-update apm

skills-install: ## Install the skills that apm.yml names. DRY_RUN=1 changes nothing
	@set -eu; \
	if [ ! -f apm.yml ]; then printf '%s\n' "skills-install: apm.yml is missing. The README of the collection has the file." >&2; exit 1; fi
	$(APM) install $(if $(DRY_RUN),--dry-run)

skills-update: ## Update the skills to the version apm.yml allows. DRY_RUN=1 changes nothing
	@set -eu; \
	if [ ! -f apm.yml ]; then printf '%s\n' "skills-update: apm.yml is missing. The README of the collection has the file." >&2; exit 1; fi
	$(APM) update $(if $(DRY_RUN),--dry-run,--yes)

apm: ## Run APM in Podman on this machine. Set ARGS.
	@set -eu; \
	if [ -z "$(ARGS)" ]; then printf '%s\n' "apm: set ARGS to the APM arguments." >&2; exit 1; fi
	$(APM) $(ARGS)

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
