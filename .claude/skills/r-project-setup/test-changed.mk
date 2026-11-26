# The test-changed target. project.mk and sdlc.mk include this file, so
# a project has the target with either include.
#
#   make coverage
#   make test-changed
#
# Set TEST_CHANGED_CMD before the include. The command reads
# build/coverage/changed.txt and selects tests from the coverage map
# that COVERAGE_CMD wrote. make test stays the full suite.

ifndef TEST_CHANGED_MK
TEST_CHANGED_MK := 1

.PHONY: test-changed

# Tests whose coverage includes a file in the diff. Not a CI substitute for test.
# help-group: Gates
test-changed: ## Run the tests that cover the diff
ifeq ($(strip $(TEST_CHANGED_CMD)),)
	@printf '%s\n' "test-changed: stub. Set TEST_CHANGED_CMD before the include. Select tests from coverage of the files in the diff." >&2
	@exit 1
else
	@set -eu; \
	mkdir -p build/coverage; \
	base=$$(git merge-base HEAD origin/$(DEFAULT_BRANCH) 2>/dev/null || git merge-base HEAD $(DEFAULT_BRANCH) 2>/dev/null || git rev-parse -q --verify HEAD 2>/dev/null || git hash-object -t tree /dev/null); \
	git diff --name-only "$$base" > build/coverage/changed.txt; \
	git diff --name-only >> build/coverage/changed.txt; \
	git diff --name-only --cached >> build/coverage/changed.txt; \
	git ls-files --others --exclude-standard >> build/coverage/changed.txt; \
	sort -u build/coverage/changed.txt -o build/coverage/changed.txt; \
	$(TEST_CHANGED_CMD)
endif

# help is the default goal. This fragment does not take it.
.DEFAULT_GOAL := help

endif
