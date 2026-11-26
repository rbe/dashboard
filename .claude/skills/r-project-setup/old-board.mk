# make old-board runs nine checks: the eight paths of the old board, and
# the old form of docs/ROADMAP.md, which has a line that starts with
# "- " instead of a table row. project.mk and the sdlc.mk of
# r-github-pipeline both include this file. It changes nothing.
#
# The target prints each path that exists and the old roadmap form, and
# then fails. An empty directory exists too, and Git does not list it.
# When no check finds anything, the target passes. While it fails, the
# only skill is r-migrate-docs.
#
# A project whose Makefile has no include yet runs
#   make -f .claude/skills/r-project-setup/old-board.mk old-board
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef OLD_BOARD_MK
OLD_BOARD_MK := 1

OLD_BOARD_PATHS := docs/BUGS.md docs/WAVES.md docs/FEATURES.md docs/DECISIONS.md docs/KNOWN_ISSUES.md docs/bugs docs/waves docs/features

.PHONY: old-board

old-board: ## Fail when a path of the old board exists, or docs/ROADMAP.md has the old line form
	@set -eu; \
	found=0; \
	for path in $(OLD_BOARD_PATHS); do \
	  if [ -d "$$path" ]; then printf 'old-board: %s/ exists\n' "$$path"; found=1; \
	  elif [ -e "$$path" ] || [ -L "$$path" ]; then printf 'old-board: %s exists\n' "$$path"; found=1; fi; \
	done; \
	if [ -f docs/ROADMAP.md ] && grep -q '^- ' docs/ROADMAP.md; then printf '%s\n' 'old-board: docs/ROADMAP.md has a line that starts with "- ". That is the old roadmap form.'; found=1; fi; \
	if [ "$$found" -ne 0 ]; then \
	  printf '%s\n' "old-board: the old board is present. The only skill is r-migrate-docs." >&2; \
	  exit 1; \
	fi; \
	printf '%s\n' "old-board: none of the eight paths exists, and docs/ROADMAP.md has no line that starts with \"- \"."

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
