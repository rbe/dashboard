# The numbers of the board merge report. project.mk and sdlc.mk include
# this file when the skill is installed. Python runs through $(PYTHON),
# which is Podman on this machine.
#
#   make board-numbers
#   make board-numbers IDS="R-51 R-76"
#
# Without IDS the target lists every in force requirement row, ADR, and
# history file. The columns are id, kind, status, words,
# tests that name the id with `id:`, links to the id from other
# documents, frontmatter lists that name the id, and names. The
# names are the tests as `file::name`, sorted, joined with `;`.

ifndef BOARD_MERGE_REPORT_MK
BOARD_MERGE_REPORT_MK := 1

BOARD_MERGE_REPORT_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

# Alone, as `make -f <this file> board-numbers`, no makefile has
# defined $(PYTHON) yet.
ifndef PYTHON
include $(BOARD_MERGE_REPORT_DIR)../r-project-setup/podman-python.mk
endif

.PHONY: board-numbers

# help-group: Board
board-numbers: ## List words, tests with their names, and links of each board unit. IDS= narrows it
	$(PYTHON) "$(BOARD_MERGE_REPORT_DIR)scripts/board_numbers.py" $(IDS)

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
