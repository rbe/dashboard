# The check-docs target. project.mk and the sdlc.mk of r-github-pipeline
# include this file, so a project has the target with either include.
#
#   make check-docs
#
# The target fails when a SKILL.md or a reference file of an installed
# skill names a path under skills/r-<name>/ or .claude/skills/r-<name>/
# that does not exist, or names `make <target>` for a target that no
# makefile of the repository defines. make test runs it first, so CI runs
# it with the test job. It changes nothing.
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef CHECK_DOCS_MK
CHECK_DOCS_MK := 1

CHECK_DOCS_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

.PHONY: check-docs

# help-group: Gates
check-docs: ## Fail when a skill text names a missing path or a missing Make target
	$(PYTHON) "$(CHECK_DOCS_DIR)scripts/check_docs.py"

test: check-docs

endif
