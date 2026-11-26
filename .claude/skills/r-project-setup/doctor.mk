# make doctor checks the tools a machine needs before any other target
# runs. project.mk and the sdlc.mk of r-github-pipeline both include this
# file. doctor is the first prerequisite of setup, so `make setup` runs
# it before any other target. It changes nothing.
#
# Checks, each printed as ok or FAIL with the fix:
#   make    GNU Make 3.81 or newer
#   git     runs
#   podman  `podman info` works. On macOS a stopped Podman machine fails
#           that command: start it with `make podman-start`
#   origin  a remote named origin, when the project has a workflow
#
# Make, Git, and Podman are the only tools the host needs. Every other
# tool runs in a Podman image behind a target.
#
# A project whose Makefile has no include yet runs
#   make -f .claude/skills/r-project-setup/doctor.mk doctor
#
# GNU Make 3.81. See project.mk for the rules of a recipe.

ifndef DOCTOR_MK
DOCTOR_MK := 1

.PHONY: doctor podman-start

doctor: ## Check that this machine has the tools the targets need
	@set -u; \
	failed=0; \
	ok() { printf '  ok    %s\n' "$$1"; }; \
	bad() { printf '  FAIL  %s\n        %s\n' "$$1" "$$2"; failed=1; }; \
	os=$$(uname -s); \
	printf '%s\n' "doctor: $$os"; \
	version=$$($(MAKE) --version 2>/dev/null | sed -n '1s/[^0-9]*\([0-9][0-9]*\)\.\([0-9][0-9]*\).*/\1 \2/p'); \
	major=$${version%% *}; minor=$${version##* }; \
	if [ -n "$$major" ] && { [ "$$major" -gt 3 ] || { [ "$$major" -eq 3 ] && [ "$$minor" -ge 81 ]; }; }; then \
	  ok "make $$major.$$minor"; \
	else \
	  bad "make is older than 3.81 or not GNU Make" "Install GNU Make 3.81 or newer."; \
	fi; \
	if git --version >/dev/null 2>&1; then ok "$$(git --version)"; \
	else bad "git does not run" "Install Git. On macOS: xcode-select --install"; fi; \
	if ! command -v podman >/dev/null 2>&1; then \
	  if [ "$$os" = "Darwin" ]; then hint="Install Podman from podman.io, then run make podman-start."; \
	  else hint="Install Podman with the package manager of this system."; fi; \
	  bad "podman is not on PATH" "$$hint"; \
	elif podman info >/dev/null 2>&1; then \
	  ok "podman runs"; \
	else \
	  if [ "$$os" = "Darwin" ]; then hint="Run make podman-start."; \
	  else hint="Run podman info and read the error."; fi; \
	  bad "podman info fails" "$$hint"; \
	fi; \
	if [ -d .github/workflows ]; then \
	  if git remote get-url origin >/dev/null 2>&1; then ok "git remote origin"; \
	  else bad "no git remote named origin" "Run git remote add origin <url>. The workflow and the image name read it."; fi; \
	fi; \
	if [ "$$failed" -ne 0 ]; then printf '%s\n' "doctor: fix the FAIL lines, then run make doctor again." >&2; exit 1; fi; \
	printf '%s\n' "doctor: ready"

podman-start: ## Start the Podman machine on macOS, and create it first when none exists
	@set -eu; \
	if [ "$$(uname -s)" != "Darwin" ]; then printf '%s\n' "podman-start: this system needs no Podman machine."; exit 0; fi; \
	if podman info >/dev/null 2>&1; then printf '%s\n' "podman-start: the Podman machine runs."; exit 0; fi; \
	podman machine start || { podman machine init && podman machine start; }

# This file is included before contract.mk and before the index.mk of
# r-record, so doctor runs before toon and before the recipe of setup.
setup: doctor

endif
