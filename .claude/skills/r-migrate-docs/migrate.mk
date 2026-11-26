# The targets of r-migrate-docs. project.mk and the sdlc.mk of
# r-github-pipeline include this file when the skill is installed.
#
#   make old-board
#   make old-board-delete
#
# old-board is old-board.mk of r-project-setup: it prints each of the eight
# paths that exists and a docs/ROADMAP.md in the old line form, and fails
# when one of these nine checks finds something. old-board-delete deletes
# the eight paths, files and directories, and then runs old-board. Run it
# only after each still-true fact has a new place, and after the roadmap
# is a table.
#
# A project whose Makefile has no include yet runs
#   make -f .claude/skills/r-migrate-docs/migrate.mk old-board
#   make -f .claude/skills/r-migrate-docs/migrate.mk old-board-delete
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef MIGRATE_MK
MIGRATE_MK := 1

MIGRATE_MK_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(MIGRATE_MK_DIR)../r-project-setup/old-board.mk

.PHONY: old-board-delete

# help-group: Board
old-board-delete: ## Delete the eight paths of the old board
	@set -eu; \
	for path in $(OLD_BOARD_PATHS); do \
	  if [ -e "$$path" ] || [ -L "$$path" ]; then rm -rf "$$path"; printf 'old-board-delete: deleted %s\n' "$$path"; fi; \
	done; \
	$(MAKE) --no-print-directory -f "$(MIGRATE_MK_DIR)migrate.mk" old-board

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
