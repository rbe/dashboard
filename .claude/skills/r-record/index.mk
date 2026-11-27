# Indexes an agent reads. project.mk and sdlc.mk include this file when
# it is installed. Python runs through $(PYTHON), which is Podman on
# this machine. podman-python.mk defines it.
#
#   make toon
#   make ids
#   make links
#   make links-check
#   make id KIND=W
#   make id-raise KIND=D TO=24
#   make req ID="R-45 R-75"
#   make req Q=podman FULL=1
#   make req OWNER=record STATUS=planned
#
# req prints the requirement rows and the ADRs that a question needs, so
# an agent reads one row and not a whole file. ID prints each named item
# in full. Q lists id, title, and file of each item whose title or
# statement holds the word, in any case. OWNER and STATUS list one owner
# or one status, and a filter combines with the others. FULL=1 adds the
# statement to a list. The ADRs of docs/adr/ are read by ID, Q, and STATUS.
# They have no owner, so OWNER lists rows only.
#
# id prints the next id of a kind (R, W, ADR, or P) and raises the
# counter of that kind in docs/ids.yaml by one. A number is never given
# twice. id-raise sets a counter to a higher number, for the ids that
# a repository already uses.
#
# toon writes docs/adr/index.toon and docs/skill-index.toon.
# A repository with docs/requirements/ and no ADR file writes
# docs/requirements-index.toon instead, and does not create docs/adr/.
# When both exist, toon writes the ADR index.
# make setup runs toon first when this file is included.

ifndef RECORD_INDEX_MK
RECORD_INDEX_MK := 1

RECORD_DIR := $(dir $(lastword $(MAKEFILE_LIST)))

ifndef PYTHON
include $(RECORD_DIR)../r-project-setup/podman-python.mk
endif

.PHONY: toon ids id id-raise req links links-check board-check

# help-group: Board
toon: ## Write the ADR or requirements index, and the skill index
	$(PYTHON) "$(RECORD_DIR)scripts/toon.py"

ids: ## Reject a repeated id, an id above its counter, and a list item that is no id
	$(PYTHON) "$(RECORD_DIR)scripts/ids.py"

id: ## Print the next id of a kind and raise its counter. Set KIND=R, W, ADR, or P
	@set -eu; \
	if [ -z "$(KIND)" ]; then printf '%s\n' "id: set KIND=<R, W, ADR, or P>" >&2; exit 1; fi; \
	$(PYTHON) "$(RECORD_DIR)scripts/ids.py" id "$(KIND)"

id-raise: ## Set the counter of a kind to a higher number. Set KIND= and TO=
	@set -eu; \
	if [ -z "$(KIND)" ] || [ -z "$(TO)" ]; then printf '%s\n' "id-raise: set KIND=<kind> and TO=<number>" >&2; exit 1; fi; \
	$(PYTHON) "$(RECORD_DIR)scripts/ids.py" raise "$(KIND)" "$(TO)"

# req takes only a value from the command line. OWNER is also the GitHub
# owner of an image in sdlc.mk, and a variable of the environment must not
# filter the rows.
REQ_ID := $(if $(filter command line,$(origin ID)),$(ID))
REQ_Q := $(if $(filter command line,$(origin Q)),$(Q))
REQ_OWNER := $(if $(filter command line,$(origin OWNER)),$(OWNER))
REQ_STATUS := $(if $(filter command line,$(origin STATUS)),$(STATUS))
REQ_FULL := $(if $(filter command line,$(origin FULL)),$(if $(FULL),--full))

req: ## Print requirement rows or ADRs. Set ID=, Q=, OWNER=, or STATUS=, and FULL=1 for statements
	@set -eu; \
	if [ -z "$(REQ_ID)$(REQ_Q)$(REQ_OWNER)$(REQ_STATUS)" ]; then printf '%s\n' "req: set ID=<ids>, Q=<word>, OWNER=<skill>, or STATUS=<status>" >&2; exit 1; fi; \
	$(PYTHON) "$(RECORD_DIR)scripts/req.py" --id "$(REQ_ID)" --q "$(REQ_Q)" --owner "$(REQ_OWNER)" --status "$(REQ_STATUS)" $(REQ_FULL)

links: ## Write a link for each id in the documents under docs/
	$(PYTHON) "$(RECORD_DIR)scripts/links.py"

links-check: ## Fail when an id in a document is not a link
	$(PYTHON) "$(RECORD_DIR)scripts/links.py" check

# The board checks in one target. make test runs it, so the gates and CI
# fail on a repeated id, an id above its counter, and an id that is not a
# link. report.mk of r-project-report adds test-ids, the test-id check.
# help-group: Board
board-check: ids links-check ## Fail on a bad id, an id that is no link, or a test with no id

test: board-check

setup: toon

# GNU Make 3.81 joins the prerequisites of two setup rules in the reverse
# order of the includes. When doctor.mk is included, toon waits for doctor,
# so doctor runs first in every Make version.
ifdef DOCTOR_MK
toon: doctor
endif

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
