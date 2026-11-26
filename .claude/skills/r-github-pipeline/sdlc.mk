# Shared pipeline makefile. A project includes this file from the
# installed skill and does not keep a second copy at the root.
#     include .claude/skills/r-github-pipeline/sdlc.mk
# The project sets
# IMAGE, PACKAGE, and KEEP_VERSIONS before the include.
#
# This file includes the contract targets of r-project-setup (setup, build,
# test, format, lint, coverage, and the others, from the command
# variables) and the image targets of container.mk (image, image-ci,
# publish-container). A project on a language makefile of its language
# skill therefore keeps those targets when it switches from project.mk to
# this file. A project does not define a contract target again. The Node
# and Gradle makefiles of this skill set the command variables too. The
# project owns the targets after the include (publish-*, run, stop).
#
# GNU Make 3.81, including the macOS system make. Recipes do not use the
# one-shell option or Make 4 functions. Each recipe is one shell, joined
# with backslashes, and does not depend on shell flags from the makefile.
# The shell is POSIX sh. A recursive make inside a recipe uses the MAKE
# environment variable, so `make -n` prints the recipe. `ci` is the
# exception: it calls $(MAKE) so a dry run walks the child targets.
#
# version: $(shell git describe), then a strict vMAJOR.MINOR.PATCH check.
# A nearer pre-release tag (v1.2.0-rc.1) fails the publish.
# Cleanups: gh api --jq. The GitHub CLI runs in Podman, in the image
# that `make gh-image` builds once from GH_BASE_IMAGE and GH_VERSION.
# The host needs no gh and no jq. The token is GH_TOKEN or GITHUB_TOKEN
# of the environment, on a laptop and in CI.
# DRY_RUN=1 prints deletions and performs none.
# A publish whose GITHUB_REF is not refs/heads/$SDLC_DEFAULT_BRANCH tags
# the version only: publish-tags omits latest, and both cleanups exit
# without deleting. A missing GHCR package (HTTP 404) deletes nothing.
# The two cleanups run at any time, with or without DRY_RUN=1, and need
# no git tag and no GITHUB_RUN_NUMBER. The kept version is PUBLISHED_TAG,
# else the content of build/publish-version.txt, else the newest rolling
# version (MAJOR.MINOR.PATCH-run) by created_at of the list from GitHub.
# A given tag that is not exactly one version in that list stops the
# cleanup, and the message names where the tag came from. A list with no
# rolling version deletes nothing and exits 0.
# The former kept is the next-lower run on that MAJOR.MINOR.PATCH line.
# A version that still wears latest, or any tag that is not
# MAJOR.MINOR.PATCH-<run>, is not deleted.
#
# Set before the include:
#   IMAGE            ghcr.io/owner/name, no tag
#   PACKAGE          GitHub owner/name. Defaults to GITHUB_REPOSITORY, else
#                    OWNER/NAME from the remote origin.
#   KEEP_VERSIONS    versions to keep, counting the one just published.
#                    Default 2 (published + one former).
#   SDLC_JOBS        report rows, in pipeline order
#   SDLC_CI          targets `ci` runs. Default includes editorconfig,
#                    format, lint, test, integration, coverage, and docs.
#   HELP_LEAD        first line of `make help`
#   GH_VERSION       the GitHub CLI release in the image
#   GH_BASE_IMAGE    the base of that image
#   GH_IMAGE         the local name of that image
#
# The CI result and pull request targets run the GitHub CLI in that
# image. The image has no Git, so a recipe reads Git on the host. The
# pull request targets call `gh api` with REST routes only, because the
# GraphQL API is not open in every network. owner/name is GH_REPO,
# which is OWNER/NAME. A command-line variable sets one run:
#   SHA              ci-status reads this commit. Default: HEAD.
#   WAIT=1           ci-status waits for the run to end.
#                    pull-request-merge waits for the checks to end.
#   TITLE, BODY      the pull request text. Default: the last commit
#                    subject and the subjects of the commits on the branch.
#   CI_WAIT_SECONDS  seconds between two polls of ci-status. Default 15.
#   CI_WAIT_TRIES    polls before ci-status stops waiting. Default 240.

ifndef SDLC_MK
SDLC_MK := 1

SDLC_MK_DIR := $(dir $(lastword $(MAKEFILE_LIST)))
include $(SDLC_MK_DIR)../r-project-setup/podman-python.mk
include $(SDLC_MK_DIR)../r-project-setup/tools.mk
include $(SDLC_MK_DIR)../r-project-setup/doctor.mk
include $(SDLC_MK_DIR)../r-project-setup/skills.mk
include $(SDLC_MK_DIR)../r-project-setup/old-board.mk
include $(SDLC_MK_DIR)../r-project-setup/test-changed.mk
-include .claude/skills/r-project-report/report.mk
include $(SDLC_MK_DIR)../r-project-setup/contract.mk
include $(SDLC_MK_DIR)container.mk

# Recipes call ${MAKE} from the shell. Make does not export this variable
# unless asked, and a recipe that writes $(MAKE) is executed even by make -n.
export MAKE

KEEP_VERSIONS ?= 2
PACKAGE ?= $(or $(GITHUB_REPOSITORY),$(if $(OWNER),$(OWNER)/$(NAME)))
SDLC_JOBS ?= setup build test docs publish-container
SDLC_CI ?= setup build editorconfig format lint test integration coverage docs report
SDLC_KEEP_ARTIFACTS ?= report,docs
SDLC_ARTIFACT_AGE ?= 3600
HELP_LEAD ?= The Makefile is the interface. A laptop and CI run the same targets.

# The GitHub CLI runs in a local image. `make gh-image` builds it once:
# the base image plus the release binary of GH_VERSION. A cleanup
# target builds it first when it is missing. gh reads GH_TOKEN or
# GITHUB_TOKEN from the environment. The work tree is /work, so a
# release asset is a path under the project.
GH_VERSION ?= 2.89.0
GH_BASE_IMAGE ?= docker.io/library/alpine:3.22
GH_IMAGE ?= localhost/sdlc-gh:$(GH_VERSION)
GH_REPO ?= $(OWNER)/$(NAME)
CI_WAIT_SECONDS ?= 15
CI_WAIT_TRIES ?= 240
GH = podman run --rm -e GH_TOKEN -e GITHUB_TOKEN -e GH_HOST -e GITHUB_RUN_ID -e SDLC_ARTIFACT_AGE -e SDLC_KEEP_ARTIFACTS $(PODMAN_NET_ARGS) -v "$(CURDIR)":/work:Z -w /work $(GH_IMAGE)

# Nearest ancestor tag whose name starts with v and a digit. Empty when
# none exists. version rejects anything that is not vMAJOR.MINOR.PATCH.
GIT_DESCRIBE = git describe --tags --abbrev=0 --match 'v[0-9]*'
GIT_TAG = $(shell $(GIT_DESCRIBE) 2>/dev/null)

# Use $(THIS_MAKE) in a recipe that must not run under `make -n`.
# A recipe that says $(MAKE) is executed even during a dry run.
THIS_MAKE := $(MAKE)

# setup, build, test, and the publish targets are phony here so a build/
# directory cannot satisfy the build target.
.PHONY: help version ci report setup build test docs publish-tags \
	publish-container publish-github image run stop clean gh-image \
	ci-status pull-request pull-request-merge \
	cleanup-container-versions cleanup-github-releases cleanup-actions-artifacts

# $(call SDLC_LOG,job,goal)
# goal is an internal target with no comma. The line that calls this must
# pass the goal as $(call SDLC_LOG,setup,_setup) and the helper runs
# $${MAKE} so a dry run does not execute the goal.
define SDLC_LOG
mkdir -p build/logs build/summaries; \
{ $${MAKE} --no-print-directory $(2); echo $$? > build/logs/$(1).status; } 2>&1 | tee build/logs/$(1).log; \
st=$$(cat build/logs/$(1).status); rm -f build/logs/$(1).status; \
if [ "$$st" -ne 0 ] && ! grep -q 'Status: failed' build/summaries/$(1).md 2>/dev/null; then \
  printf '# %s\n\nStatus: failed\n\nExit %s. See build/logs/%s.log.\n' '$(1)' "$$st" '$(1)' > build/summaries/$(1).md; \
fi; \
exit $$st
endef

# Expanded inside a cleanup recipe. Reads PUBLISHED_TAG, then
# build/publish-version.txt, else the tag is empty. It never calls
# `version`, so it needs no git tag and no GITHUB_RUN_NUMBER. Result is
# the shell variables tag and tag_from. An empty tag makes the recipe
# take the newest rolling version of the list from GitHub.
define SDLC_TAG
tag="$(PUBLISHED_TAG)"; tag_from=PUBLISHED_TAG; \
if [ -z "$$tag" ] && [ -f build/publish-version.txt ]; then tag=$$(cat build/publish-version.txt); tag_from=build/publish-version.txt; fi; \
if [ -n "$$tag" ]; then printf '%s\n' "$$tag" | grep -Eq '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-[1-9][0-9]*$$' \
  || { echo "Publish tag '$$tag' from $$tag_from is not MAJOR.MINOR.PATCH-run. Refusing to delete." >&2; exit 1; }; fi
endef

# Sets on_default=1 when this publish moves latest and may delete old versions.
# No GITHUB_REF (a laptop) does. CI does only when GITHUB_REF is
# refs/heads/$SDLC_DEFAULT_BRANCH. The workflow sets that from
# github.event.repository.default_branch. Any other ref tags the version
# only: no latest, and cleanup exits without deleting.
define SDLC_ON_DEFAULT
ref="$${GITHUB_REF:-}"; def="$${SDLC_DEFAULT_BRANCH:-}"; \
if [ -z "$$ref" ]; then on_default=1; \
elif [ -n "$$def" ] && [ "$$ref" = "refs/heads/$$def" ]; then on_default=1; \
else on_default=0; fi
endef

# Sets repo to owner/name. Stops when OWNER or NAME is empty.
define SDLC_GH_REPO
repo="$(GH_REPO)"; \
case "$$repo" in \
  ""|/*|*/) echo "Set OWNER and NAME, the GitHub owner and the repository name." >&2; exit 1 ;; \
esac; \
if [ -z "$${GH_TOKEN:-}$${GITHUB_TOKEN:-}" ]; then echo "Set GH_TOKEN or GITHUB_TOKEN. gh reads no other login." >&2; exit 1; fi
endef

# Sets branch to the current branch. Stops on a detached HEAD and on the default branch.
define SDLC_BRANCH
branch=$$(git rev-parse --abbrev-ref HEAD); \
if [ "$$branch" = HEAD ] || [ "$$branch" = "$(DEFAULT_BRANCH)" ]; then \
  echo "Check out the branch of the slice. The branch is '$$branch', and the default branch is $(DEFAULT_BRANCH)." >&2; exit 1; \
fi
endef

publish-tags: ## Print tags to push. latest only on the default branch
	@set -eu; \
	tag=$$($(THIS_MAKE) -s --no-print-directory version); \
	printf '%s\n' "$$tag"; \
	$(SDLC_ON_DEFAULT); \
	if [ "$$on_default" -eq 1 ]; then printf '%s\n' latest; fi

help: ## Show the targets. A "Match CI" line is a target the workflow runs
	@printf '%s\n' "$(HELP_LEAD)"
	@printf '%s\n' "make ci runs $(SDLC_CI). It does not publish."
	@printf '%s\n' "Podman is the only container engine."
	@printf '%s\n' ""
	@awk -v docs="$(RENDER_DOCS)" -v login="$(PUBLISH_IMAGE)" 'BEGIN {FS = ":.*## "}; /^# help-docs$$/ { skip = (docs != "1"); next } /^# help-login$$/ { skip = (login != "1"); next } /^endif$$/ { skip = 0; next } skip { next } /^[a-zA-Z][a-zA-Z0-9_-]*:.*## / && !seen[$$1]++ {printf "  %-32s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

gh-image: ## Build the image of the GitHub CLI, once
	@set -eu; \
	if podman image exists "$(GH_IMAGE)"; then exit 0; fi; \
	printf '%s\n' \
	  'FROM $(GH_BASE_IMAGE)' \
	  'ARG GH_VERSION' \
	  'RUN set -eu; case "$$(uname -m)" in x86_64) arch=amd64 ;; aarch64|arm64) arch=arm64 ;; *) echo "gh-image: no GitHub CLI for $$(uname -m)" >&2; exit 1 ;; esac; name="gh_$${GH_VERSION}_linux_$${arch}"; wget -q -O /tmp/gh.tar.gz "https://github.com/cli/cli/releases/download/v$${GH_VERSION}/$${name}.tar.gz"; tar -xzf /tmp/gh.tar.gz -C /tmp; mv "/tmp/$${name}/bin/gh" /usr/local/bin/gh; rm -r /tmp/gh.tar.gz "/tmp/$${name}"' \
	  'ENTRYPOINT ["gh"]' \
	| podman build $(PODMAN_NET_ARGS) --build-arg GH_VERSION="$(GH_VERSION)" -t "$(GH_IMAGE)" -f - . >&2

ci-status: ## Print the CI result of HEAD (SHA=<sha>). WAIT=1 waits for the end. Fails unless the run passed
	@set -eu; \
	$(SDLC_GH_REPO); \
	sha="$${SHA:-}"; \
	if [ -z "$$sha" ]; then sha=$$(git rev-parse HEAD); fi; \
	$(THIS_MAKE) --no-print-directory gh-image; \
	tab=$$(printf '\t'); tries=0; \
	while :; do \
	  row=$$($(GH) run list -R "$$repo" --commit "$$sha" --limit 1 --json workflowName,status,conclusion,url --jq '.[] | [.workflowName, .status, (.conclusion // ""), .url] | @tsv'); \
	  name=$$(printf '%s\n' "$$row" | awk -F "$$tab" '{ print $$1 }'); \
	  state=$$(printf '%s\n' "$$row" | awk -F "$$tab" '{ print $$2 }'); \
	  result=$$(printf '%s\n' "$$row" | awk -F "$$tab" '{ print $$3 }'); \
	  url=$$(printf '%s\n' "$$row" | awk -F "$$tab" '{ print $$4 }'); \
	  if [ "$$state" = completed ] || [ "$${WAIT:-}" != 1 ]; then break; fi; \
	  tries=$$((tries + 1)); \
	  if [ "$$tries" -ge "$(CI_WAIT_TRIES)" ]; then break; fi; \
	  sleep "$(CI_WAIT_SECONDS)"; \
	done; \
	if [ -z "$$state" ]; then echo "ci-status: no CI run for commit $$sha." >&2; exit 1; fi; \
	if [ "$$state" != completed ]; then echo "ci-status: $$name is $$state for commit $$sha. It is not finished. $$url" >&2; exit 1; fi; \
	echo "ci-status: $$name $$result for commit $$sha. $$url"; \
	if [ "$$result" != success ]; then exit 1; fi

pull-request: ## Open a pull request from this branch to the default branch. TITLE and BODY are optional
	@set -eu; \
	$(SDLC_GH_REPO); \
	$(SDLC_BRANCH); \
	$(THIS_MAKE) --no-print-directory gh-image; \
	open=$$($(GH) api "repos/$$repo/pulls?head=$${repo%%/*}:$$branch&base=$(DEFAULT_BRANCH)&state=open" --jq '.[0].html_url // empty'); \
	if [ -n "$$open" ]; then echo "$$open"; exit 0; fi; \
	title="$${TITLE:-}"; \
	if [ -z "$$title" ]; then title=$$(git log -1 --format=%s); fi; \
	body="$${BODY:-}"; \
	if [ -z "$$body" ]; then body=$$(git log --format='- %s' "origin/$(DEFAULT_BRANCH)..HEAD" 2>/dev/null || true); fi; \
	$(GH) api -X POST "repos/$$repo/pulls" -f title="$$title" -f head="$$branch" -f base="$(DEFAULT_BRANCH)" -f body="$$body" --jq .html_url

pull-request-merge: ## Merge the pull request of this branch when its checks passed. WAIT=1 waits for the checks
	@set -eu; \
	$(SDLC_GH_REPO); \
	$(SDLC_BRANCH); \
	$(THIS_MAKE) --no-print-directory gh-image; \
	tab=$$(printf '\t'); tries=0; \
	row=$$($(GH) api "repos/$$repo/pulls?head=$${repo%%/*}:$$branch&base=$(DEFAULT_BRANCH)&state=open" --jq '.[0] | select(. != null) | [(.number | tostring), .head.sha] | @tsv'); \
	number=$$(printf '%s\n' "$$row" | awk -F "$$tab" '{ print $$1 }'); \
	sha=$$(printf '%s\n' "$$row" | awk -F "$$tab" '{ print $$2 }'); \
	if [ -z "$$number" ]; then echo "pull-request-merge: no open pull request from $$branch. Run make pull-request first." >&2; exit 1; fi; \
	while :; do \
	  raw=$$($(GH) api --paginate "repos/$$repo/commits/$$sha/check-runs?per_page=100" --jq '[(.check_runs | length), ([.check_runs[] | select(.status != "completed")] | length), ([.check_runs[] | select(.status == "completed") | select((.conclusion == "success" or .conclusion == "skipped" or .conclusion == "neutral") | not)] | length)] | @tsv'); \
	  counts=$$(printf '%s\n' "$$raw" | awk -F "$$tab" '{ t += $$1; p += $$2; f += $$3 } END { print t + 0, p + 0, f + 0 }'); \
	  set -- $$counts; total=$$1; pending=$$2; failed=$$3; \
	  if [ "$$failed" -gt 0 ] || [ "$$pending" -eq 0 ] || [ "$${WAIT:-}" != 1 ]; then break; fi; \
	  tries=$$((tries + 1)); \
	  if [ "$$tries" -ge "$(CI_WAIT_TRIES)" ]; then break; fi; \
	  sleep "$(CI_WAIT_SECONDS)"; \
	done; \
	if [ "$$total" -eq 0 ]; then echo "pull-request-merge: pull request $$number has no checks. Nothing merged." >&2; exit 1; fi; \
	if [ "$$failed" -gt 0 ] || [ "$$pending" -gt 0 ]; then echo "pull-request-merge: the checks of pull request $$number did not pass. Nothing merged." >&2; exit 1; fi; \
	$(GH) api -X PUT "repos/$$repo/pulls/$$number/merge" -f merge_method=merge -f sha="$$sha" --jq .message

version: ## Print MAJOR.MINOR.PATCH-run. PRINT=tag prints the vX.Y.Z tag
	@set -eu; \
	tag="$(GIT_TAG)"; \
	if [ -z "$$tag" ] && [ "$$(git rev-parse --is-shallow-repository 2>/dev/null || printf '%s' false)" = true ]; then \
	  GIT_TERMINAL_PROMPT=0 git fetch --quiet --force --tags origin >&2 || true; \
	  tag="$$($(GIT_DESCRIBE) 2>/dev/null || true)"; \
	fi; \
	printf '%s\n' "$$tag" | grep -Eq '^v(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$$' \
	  || { echo "No strict vMAJOR.MINOR.PATCH tag is nearest to HEAD (got '$${tag:-none}'). Refusing to invent a version." >&2; exit 1; }; \
	if [ "$(PRINT)" = tag ]; then printf '%s\n' "$$tag"; exit 0; fi; \
	printf '%s\n' "$(GITHUB_RUN_NUMBER)" | grep -Eq '^[1-9][0-9]*$$' \
	  || { echo "GITHUB_RUN_NUMBER must be a positive integer. Refusing to invent a build number." >&2; exit 1; }; \
	printf '%s-%s\n' "$${tag#v}" "$(GITHUB_RUN_NUMBER)"

ci: ## Run the local CI targets, in order. Does not publish
	@set -eu; for t in $(SDLC_CI); do \
	  $(MAKE) --no-print-directory "$$t"; \
	  key=$$(printf '%s' "$$t" | tr 'a-z-' 'A-Z_'); \
	  eval "JOB_RESULT_$$key=success; export JOB_RESULT_$$key"; \
	done

report: ## Match CI: write build/report/index.md from logs, summaries, and job results
	@set -eu; \
	mkdir -p build/logs build/summaries build/report; \
	out=build/report; \
	rm -rf "$$out"; \
	mkdir -p "$$out/jobs/local"; \
	if [ -d build/inputs ]; then cp -R build/inputs/. "$$out/jobs/"; fi; \
	for d in logs summaries test-results coverage reports; do \
	  if [ -d "build/$$d" ]; then cp -R "build/$$d" "$$out/jobs/local/$$d"; fi; \
	done; \
	rm -f "$$out/jobs/local/logs/report.log"; \
	ref="$${GITHUB_REF:-}"; \
	if [ -z "$$ref" ]; then ref="$$(git rev-parse --abbrev-ref HEAD 2>/dev/null || printf '%s' unknown)"; fi; \
	sha="$${GITHUB_SHA:-}"; \
	if [ -z "$$sha" ]; then sha="$$(git rev-parse HEAD 2>/dev/null || printf '%s' unknown)"; fi; \
	{ \
	  echo "# Pipeline report"; \
	  echo; \
	  echo "| | |"; \
	  echo "| --- | --- |"; \
	  echo "| Repository | $${GITHUB_REPOSITORY:-$(PACKAGE)} |"; \
	  echo "| Ref | $$ref |"; \
	  echo "| Commit | $$sha |"; \
	  echo "| Event | $${GITHUB_EVENT_NAME:-local} |"; \
	  echo "| Selected job | $${DISPATCH_JOB:-none} |"; \
	  echo "| Run | $${GITHUB_RUN_NUMBER:-local} |"; \
	  echo; \
	  echo "## Jobs"; \
	  echo; \
	  echo "| Job | Result |"; \
	  echo "| --- | --- |"; \
	  for job in $(SDLC_JOBS) report; do \
	    if [ "$$job" = report ]; then continue; fi; \
	    key=$$(printf '%s' "$$job" | tr 'a-z-' 'A-Z_'); \
	    result=$$(awk -v k="JOB_RESULT_$$key" 'BEGIN { print ENVIRON[k] }'); \
	    if [ -z "$$result" ]; then result="not recorded"; fi; \
	    printf '| %s | %s |\n' "$$job" "$$result"; \
	  done; \
	  echo; \
	  find "$$out/jobs" -type f -name '*.md' | sort | while IFS= read -r f; do \
	    sed 's/^# /## /' "$$f"; \
	    echo; \
	  done; \
	  echo "## Files"; \
	  echo; \
	  find "$$out/jobs" -type f | sed "s|^$$out/||" | sort | sed 's/^/- /'; \
	} > "$$out/index.md"; \
	if [ -n "$${GITHUB_STEP_SUMMARY:-}" ]; then cat "$$out/index.md" >> "$$GITHUB_STEP_SUMMARY"; fi; \
	test -s "$$out/index.md"; \
	echo "Wrote $$out/index.md" | tee build/logs/report.log; \
	printf '# report\n\nWrote %s\n' "$$out/index.md" > build/summaries/report.md

cleanup-container-versions: ## Match CI: on the default branch, keep this run and the next-lower run
	@set -eu; \
	mkdir -p build/logs build/summaries; \
	status=failed; kept=0; deleted=0; reason="cleanup did not finish"; \
	finish() { printf '# cleanup-container-versions\n\nStatus: %s\nKept: %s\nDeleted: %s\n\n%s\n' "$$status" "$$kept" "$$deleted" "$$reason" > build/summaries/cleanup-container-versions.md; printf 'status=%s\nkept=%s\ndeleted=%s\nreason=%s\n' "$$status" "$$kept" "$$deleted" "$$reason"; }; \
	trap finish EXIT; \
	$(SDLC_ON_DEFAULT); \
	if [ "$$on_default" -eq 0 ]; then status=kept; reason="Ref is not the default branch. Tagged the version only. Nothing deleted."; exit 0; fi; \
	$(SDLC_TAG); \
	$(THIS_MAKE) --no-print-directory gh-image; \
	image="$(IMAGE)"; \
	case "$$image" in \
	  ghcr.io/*/*) ;; \
	  *) reason="IMAGE must be ghcr.io/owner/name, with no tag."; echo "$$reason" >&2; exit 1 ;; \
	esac; \
	rest=$${image#ghcr.io/}; \
	owner=$${rest%%/*}; \
	name=$${rest#*/}; \
	name=$$(printf '%s' "$$name" | sed 's|/|%2F|g'); \
	kind=$$($(GH) api "users/$$owner" --jq .type); \
	case "$$kind" in \
	  Organization) base="orgs/$$owner/packages/container/$$name" ;; \
	  *) base="users/$$owner/packages/container/$$name" ;; \
	esac; \
	tab=$$(printf '\t'); \
	err=build/logs/cleanup-container-versions.gh-err; code=0; \
	versions=$$($(GH) api --paginate "$$base/versions?per_page=100" --jq '.[] | [(.id|tostring), .created_at, ((.metadata.container.tags // []) | join(","))] | @tsv' 2>"$$err") || code=$$?; \
	if [ "$$code" -ne 0 ]; then \
	  if grep -q 404 "$$err"; then versions=""; \
	  else cat "$$err" >&2; reason="Could not list package versions."; exit 1; fi; \
	fi; \
	if [ -z "$$versions" ]; then status=kept; reason="No package versions. A missing GHCR package (HTTP 404) is an empty list. Nothing deleted."; exit 0; fi; \
	code=0; \
	plan=$$(printf '%s\n' "$$versions" | awk -F "$$tab" -v tag="$$tag" -v keep="$(KEEP_VERSIONS)" ' \
	  function rolling(t) { return t ~ /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-[1-9][0-9]*$$/ } \
	  function runof(t) { sub(/^.*-/, "", t); return t + 0 } \
	  NF < 2 { next } \
	  { n++; id[n] = $$1; created[n] = $$2 ""; protected[n] = 0; nt[n] = split($$3, parts, ","); \
	    for (i = 1; i <= nt[n]; i++) { p = parts[i]; tg[n, i] = p; if (p == "") continue; seen[p]++; owner[p] = n; \
	      if (!rolling(p)) protected[n] = 1; \
	      else if (newest[n] == "" || runof(p) > runof(newest[n])) newest[n] = p } } \
	  END { \
	    if (tag == "") { best = 0; \
	      for (i = 1; i <= n; i++) if (newest[i] != "" && (best == 0 || created[i] > created[best])) best = i; \
	      if (best == 0) exit 3; \
	      tag = newest[best] } \
	    if (seen[tag] != 1) exit 2; \
	    cur = owner[tag]; line = tag; sub(/-[^-]*$$/, "", line); run = runof(tag); \
	    print "tag", tag; \
	    print "keep", id[cur]; \
	    for (i = 1; i <= n; i++) { ver_run[i] = -1; \
	      for (k = 1; k <= nt[i]; k++) { p = tg[i, k]; if (rolling(p) && index(p, line "-") == 1) { r = runof(p); if (r > ver_run[i]) ver_run[i] = r } } } \
	    extra = keep + 0 - 1; \
	    while (extra > 0) { best = -1; \
	      for (i = 1; i <= n; i++) { r = ver_run[i]; if (i == cur || r < 0 || r >= run + 0 || picked[r]) continue; if (best < 0 || r > best) best = r } \
	      if (best < 0) break; picked[best] = 1; extra-- } \
	    for (i = 1; i <= n; i++) { if (i == cur) continue; \
	      if (ver_run[i] >= 0 && picked[ver_run[i]]) { print "keep", id[i]; continue } \
	      if (protected[i]) continue; \
	      print "delete", id[i] } \
	  }') || code=$$?; \
	if [ "$$code" -eq 3 ]; then status=kept; reason="No rolling version MAJOR.MINOR.PATCH-run in the package. Nothing deleted."; exit 0; fi; \
	if [ "$$code" -ne 0 ]; then \
	  reason="Tag $$tag from $$tag_from is not exactly one package version. Refusing to delete."; \
	  echo "$$reason" >&2; \
	  exit 1; \
	fi; \
	tag=$$(printf '%s\n' "$$plan" | awk '$$1 == "tag" { print $$2; exit }'); \
	kept=$$(printf '%s\n' "$$plan" | grep -c '^keep ' || true); \
	deleted=$$(printf '%s\n' "$$plan" | grep -c '^delete ' || true); \
	printf '%s\n' "$$plan" | while read -r action id; do \
	  if [ "$$action" != delete ]; then continue; fi; \
	  if [ -n "$(DRY_RUN)" ]; then echo "would delete package version $$id"; \
	  else $(GH) api -X DELETE "$$base/versions/$$id" >/dev/null; echo "deleted package version $$id"; fi; \
	done; \
	if [ "$$deleted" -eq 0 ]; then status=kept; reason="Kept $$tag and the next-lower run on that line. Versions that wear latest or a non-rolling tag were left in place."; \
	elif [ -n "$(DRY_RUN)" ]; then status=dry-run; reason="Would delete $$deleted rolling version(s). Kept $$tag and the next-lower run. Nothing deleted."; \
	else status=deleted; reason="Kept $$tag and the next-lower run on that line. Versions that wear latest or a non-rolling tag were left in place."; fi

cleanup-github-releases: ## Match CI: on the default branch, keep this release and the next-lower run
	@set -eu; \
	mkdir -p build/logs build/summaries; \
	status=failed; kept=0; deleted=0; reason="cleanup did not finish"; \
	finish() { printf '# cleanup-github-releases\n\nStatus: %s\nKept: %s\nDeleted: %s\n\n%s\n' "$$status" "$$kept" "$$deleted" "$$reason" > build/summaries/cleanup-github-releases.md; printf 'status=%s\nkept=%s\ndeleted=%s\nreason=%s\n' "$$status" "$$kept" "$$deleted" "$$reason"; }; \
	trap finish EXIT; \
	$(SDLC_ON_DEFAULT); \
	if [ "$$on_default" -eq 0 ]; then status=kept; reason="Ref is not the default branch. Tagged the version only. Nothing deleted."; exit 0; fi; \
	$(SDLC_TAG); \
	$(THIS_MAKE) --no-print-directory gh-image; \
	repo="$(PACKAGE)"; \
	if [ -z "$$repo" ]; then reason="PACKAGE is empty. Set it to owner/name."; echo "$$reason" >&2; exit 1; fi; \
	tab=$$(printf '\t'); \
	releases=$$($(GH) api --paginate "repos/$$repo/releases?per_page=100" --jq '.[] | [(.id|tostring), .tag_name, .created_at] | @tsv'); \
	code=0; \
	plan=$$(printf '%s\n' "$$releases" | awk -F "$$tab" -v tag="$$tag" -v keep="$(KEEP_VERSIONS)" ' \
	  function rolling(t) { return t ~ /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-[1-9][0-9]*$$/ } \
	  function runof(t) { sub(/^.*-/, "", t); return t + 0 } \
	  NF < 3 { next } \
	  { n++; id[n] = $$1; name[n] = $$2; created[n] = $$3 ""; seen[$$2]++; owner[$$2] = n } \
	  END { \
	    if (tag == "") { best = 0; \
	      for (i = 1; i <= n; i++) if (rolling(name[i]) && (best == 0 || created[i] > created[best])) best = i; \
	      if (best == 0) exit 3; \
	      tag = name[best] } \
	    if (seen[tag] != 1) exit 2; \
	    cur = owner[tag]; line = tag; sub(/-[^-]*$$/, "", line); run = runof(tag); \
	    for (i = 1; i <= n; i++) ver_run[i] = (rolling(name[i]) && index(name[i], line "-") == 1) ? runof(name[i]) : -1; \
	    print "tag", tag; \
	    print "keep", id[cur], name[cur]; \
	    extra = keep + 0 - 1; \
	    while (extra > 0) { best = -1; \
	      for (i = 1; i <= n; i++) { r = ver_run[i]; if (i == cur || r < 0 || r >= run + 0 || picked[r]) continue; if (best < 0 || r > best) best = r } \
	      if (best < 0) break; picked[best] = 1; extra-- } \
	    for (i = 1; i <= n; i++) { if (i == cur) continue; \
	      if (ver_run[i] >= 0 && picked[ver_run[i]]) { print "keep", id[i], name[i]; continue } \
	      if (!rolling(name[i])) continue; \
	      print "delete", id[i], name[i] } \
	  }') || code=$$?; \
	if [ "$$code" -eq 3 ]; then status=kept; reason="No rolling release MAJOR.MINOR.PATCH-run. Nothing deleted."; exit 0; fi; \
	if [ "$$code" -ne 0 ]; then \
	  reason="Release $$tag from $$tag_from is not exactly one release. Refusing to delete."; \
	  echo "$$reason" >&2; \
	  exit 1; \
	fi; \
	tag=$$(printf '%s\n' "$$plan" | awk '$$1 == "tag" { print $$2; exit }'); \
	kept=$$(printf '%s\n' "$$plan" | grep -c '^keep ' || true); \
	deleted=$$(printf '%s\n' "$$plan" | grep -c '^delete ' || true); \
	printf '%s\n' "$$plan" | while read -r action id name; do \
	  if [ "$$action" != delete ]; then continue; fi; \
	  case "$$name" in v*) echo "skip $$name: a v* tag is a version, not a build release"; continue ;; esac; \
	  if [ -n "$(DRY_RUN)" ]; then echo "would delete release $$name"; \
	  else \
	    $(GH) api -X DELETE "repos/$$repo/releases/$$id" >/dev/null; \
	    $(GH) api -X DELETE "repos/$$repo/git/refs/tags/$$name" >/dev/null; \
	    echo "deleted release $$name"; \
	  fi; \
	done; \
	if [ "$$deleted" -eq 0 ]; then status=kept; reason="Nothing older than the $$kept kept release(s). v* tags were not deleted."; \
	elif [ -n "$(DRY_RUN)" ]; then status=dry-run; reason="Would delete $$deleted release(s). Kept $$tag and $$((kept - 1)) former. v* tags were not deleted. Nothing deleted."; \
	else status=deleted; reason="Kept $$tag and $$((kept - 1)) former. v* tags were not deleted."; fi

cleanup-actions-artifacts: ## Match CI: delete artifacts at least one hour old, except this run, report, and docs
	@set -eu; \
	mkdir -p build/logs build/summaries; \
	repo="$(PACKAGE)"; \
	if [ -z "$$repo" ]; then echo "PACKAGE is empty. Set it to owner/name." >&2; exit 1; fi; \
	export GITHUB_RUN_ID="$${GITHUB_RUN_ID:-0}"; \
	export SDLC_ARTIFACT_AGE="$(SDLC_ARTIFACT_AGE)"; \
	export SDLC_KEEP_ARTIFACTS="$(SDLC_KEEP_ARTIFACTS)"; \
	$(THIS_MAKE) --no-print-directory gh-image; \
	tab=$$(printf '\t'); \
	ids=$$($(GH) api --paginate "repos/$$repo/actions/artifacts?per_page=100" --jq '.artifacts[] | select(.expired | not) | select((.workflow_run.id // 0) != (env.GITHUB_RUN_ID | tonumber)) | select(.name as $$n | (env.SDLC_KEEP_ARTIFACTS | split(",")) | index($$n) | not) | select((now - (.created_at | fromdateiso8601)) >= (env.SDLC_ARTIFACT_AGE | tonumber)) | [(.id|tostring), .name, (.size_in_bytes|tostring)] | @tsv'); \
	count=0; \
	if [ -n "$$ids" ]; then \
	  printf '%s\n' "$$ids" | while IFS="$$tab" read -r id name size; do \
	    if [ -z "$$id" ]; then continue; fi; \
	    if [ -n "$(DRY_RUN)" ]; then echo "would delete artifact $$id $$name ($$size bytes)"; \
	    else $(GH) api -X DELETE "repos/$$repo/actions/artifacts/$$id" >/dev/null; echo "deleted artifact $$id $$name ($$size bytes)"; fi; \
	  done; \
	  count=$$(printf '%s\n' "$$ids" | grep -c . || true); \
	fi; \
	if [ "$$count" -eq 0 ]; then word=kept; elif [ -n "$(DRY_RUN)" ]; then word=dry-run; else word=deleted; fi; \
	reason="$$count artifact(s) at least $(SDLC_ARTIFACT_AGE)s old, excluding run $$GITHUB_RUN_ID and [$(SDLC_KEEP_ARTIFACTS)]."; \
	if [ -n "$(DRY_RUN)" ]; then reason="$$reason Nothing deleted."; fi; \
	printf '# cleanup-actions-artifacts\n\nStatus: %s\nDeleted: %s\n\n%s\n' "$$word" "$$count" "$$reason" > build/summaries/cleanup-actions-artifacts.md; \
	echo "cleanup-actions-artifacts: $$reason"

-include .claude/skills/r-record/index.mk
-include .claude/skills/r-project-report/report.mk
-include .claude/skills/r-migrate-docs/migrate.mk
-include .claude/skills/r-board-merge-report/merge-report.mk

# After the fragments this file includes. A fragment must not replace it.
.DEFAULT_GOAL := help

endif
