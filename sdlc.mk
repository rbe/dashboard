# Shared pipeline makefile. Copy it unchanged to the repository root as
# sdlc.mk and include it from the project Makefile. The project sets
# IMAGE, PACKAGE, and KEEP_VERSIONS before the include, and it owns the
# project targets (setup, build, test, docs, publish-*, image, run, stop).
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
# Cleanups: gh api --jq. DRY_RUN=1 prints deletions and performs none.
#
# Set before the include:
#   IMAGE            ghcr.io/owner/name, no tag
#   PACKAGE          GitHub owner/name. Defaults to GITHUB_REPOSITORY.
#   KEEP_VERSIONS    versions to keep, counting the one just published.
#                    Default 2 (published + one former).
#   SDLC_JOBS        report rows, in pipeline order
#   SDLC_CI          targets `ci` runs. Default includes docs.
#   HELP_LEAD        first line of `make help`

ifndef SDLC_MK
SDLC_MK := 1

# Recipes call ${MAKE} from the shell. Make does not export this variable
# unless asked, and a recipe that writes $(MAKE) is executed even by make -n.
export MAKE

KEEP_VERSIONS ?= 2
PACKAGE ?= $(GITHUB_REPOSITORY)
SDLC_JOBS ?= setup build test docs publish-container
SDLC_CI ?= setup build test docs report
SDLC_KEEP_ARTIFACTS ?= report,docs
SDLC_ARTIFACT_AGE ?= 3600
HELP_LEAD ?= The Makefile is the interface. A laptop and CI run the same targets.

# Nearest ancestor tag whose name starts with v and a digit. Empty when
# none exists. version rejects anything that is not vMAJOR.MINOR.PATCH.
GIT_DESCRIBE = git describe --tags --abbrev=0 --match 'v[0-9]*'
GIT_TAG = $(shell $(GIT_DESCRIBE) 2>/dev/null)

# Use $(THIS_MAKE) in a recipe that must not run under `make -n`.
# A recipe that says $(MAKE) is executed even during a dry run.
.DEFAULT_GOAL := help
THIS_MAKE := $(MAKE)

# setup, build, test, and the publish targets are phony here so a build/
# directory cannot satisfy the build target.
.PHONY: help version ci report setup build test docs \
	publish-container publish-github image run stop clean \
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
# build/publish-version.txt, then `version`. Result is shell variable tag.
define SDLC_TAG
tag="$(PUBLISHED_TAG)"; \
if [ -z "$$tag" ] && [ -f build/publish-version.txt ]; then tag=$$(cat build/publish-version.txt); fi; \
if [ -z "$$tag" ]; then tag=$$($(THIS_MAKE) -s --no-print-directory version); fi; \
printf '%s\n' "$$tag" | grep -Eq '^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-[1-9][0-9]*$$' \
  || { echo "Publish tag '$$tag' is not MAJOR.MINOR.PATCH-run. Refusing to delete." >&2; exit 1; }
endef

help: ## Show the targets. A "Match CI" line is a target the workflow runs
	@printf '%s\n' "$(HELP_LEAD)"
	@printf '%s\n' "make ci runs $(SDLC_CI). It does not publish."
	@printf '%s\n' "Podman is the only container engine."
	@printf '%s\n' ""
	@awk 'BEGIN {FS = ":.*## "}; /^[a-zA-Z][a-zA-Z0-9_-]*:.*## / {printf "  %-32s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

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

ci: ## Run setup, build, test, docs, and report, in that order. Does not publish
	@set -eu; for t in $(SDLC_CI); do $(MAKE) --no-print-directory "$$t"; done

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

cleanup-container-versions: ## Match CI: keep the published image version and one former
	@set -eu; \
	mkdir -p build/logs build/summaries; \
	status=failed; kept=0; deleted=0; reason="cleanup did not finish"; \
	finish() { printf '# cleanup-container-versions\n\nStatus: %s\nKept: %s\nDeleted: %s\n\n%s\n' "$$status" "$$kept" "$$deleted" "$$reason" > build/summaries/cleanup-container-versions.md; printf 'status=%s\nkept=%s\ndeleted=%s\nreason=%s\n' "$$status" "$$kept" "$$deleted" "$$reason"; }; \
	trap finish EXIT; \
	$(SDLC_TAG); \
	image="$(IMAGE)"; \
	case "$$image" in \
	  ghcr.io/*/*) ;; \
	  *) reason="IMAGE must be ghcr.io/owner/name, with no tag."; echo "$$reason" >&2; exit 1 ;; \
	esac; \
	rest=$${image#ghcr.io/}; \
	owner=$${rest%%/*}; \
	name=$${rest#*/}; \
	name=$$(printf '%s' "$$name" | sed 's|/|%2F|g'); \
	kind=$$(gh api "users/$$owner" --jq .type); \
	case "$$kind" in \
	  Organization) base="orgs/$$owner/packages/container/$$name" ;; \
	  *) base="users/$$owner/packages/container/$$name" ;; \
	esac; \
	tab=$$(printf '\t'); \
	versions=$$(gh api --paginate "$$base/versions?per_page=100" --jq '.[] | [(.id|tostring), .created_at, ((.metadata.container.tags // []) | join(","))] | @tsv'); \
	if ! plan=$$(printf '%s\n' "$$versions" | awk -F "$$tab" -v tag="$$tag" -v keep="$(KEEP_VERSIONS)" ' \
	  NF < 2 { next } \
	  { n++; id[n] = $$1; created[n] = $$2; s = "," $$3 ","; if (index(s, "," tag ",") > 0) { hits++; cur = n } } \
	  END { \
	    if (hits != 1) exit 2; \
	    keptn = 1; print "keep", id[cur]; \
	    while (keptn < keep + 0) { \
	      best = 0; \
	      for (i = 1; i <= n; i++) { \
	        if (i == cur || seen[i]) continue; \
	        if (best == 0 || created[i] > created[best]) best = i; \
	      } \
	      if (best == 0) break; \
	      seen[best] = 1; keptn++; print "keep", id[best]; \
	    } \
	    for (i = 1; i <= n; i++) if (i != cur && !seen[i]) print "delete", id[i]; \
	  }'); then \
	  reason="Tag $$tag is not exactly one package version. Refusing to delete."; \
	  echo "$$reason" >&2; \
	  exit 1; \
	fi; \
	kept=$$(printf '%s\n' "$$plan" | grep -c '^keep ' || true); \
	deleted=$$(printf '%s\n' "$$plan" | grep -c '^delete ' || true); \
	printf '%s\n' "$$plan" | while read -r action id; do \
	  if [ "$$action" != delete ]; then continue; fi; \
	  if [ -n "$(DRY_RUN)" ]; then echo "would delete package version $$id"; \
	  else gh api -X DELETE "$$base/versions/$$id" >/dev/null; echo "deleted package version $$id"; fi; \
	done; \
	if [ "$$deleted" -eq 0 ]; then status=kept; reason="Nothing older than the $$kept kept version(s)."; \
	elif [ -n "$(DRY_RUN)" ]; then status=dry-run; reason="Would delete $$deleted version(s). Kept $$tag and $$((kept - 1)) former. Nothing deleted."; \
	else status=deleted; reason="Kept $$tag and $$((kept - 1)) former."; fi

cleanup-github-releases: ## Match CI: keep the published release and one former. Never delete a v* tag
	@set -eu; \
	mkdir -p build/logs build/summaries; \
	status=failed; kept=0; deleted=0; reason="cleanup did not finish"; \
	finish() { printf '# cleanup-github-releases\n\nStatus: %s\nKept: %s\nDeleted: %s\n\n%s\n' "$$status" "$$kept" "$$deleted" "$$reason" > build/summaries/cleanup-github-releases.md; printf 'status=%s\nkept=%s\ndeleted=%s\nreason=%s\n' "$$status" "$$kept" "$$deleted" "$$reason"; }; \
	trap finish EXIT; \
	$(SDLC_TAG); \
	repo="$(PACKAGE)"; \
	if [ -z "$$repo" ]; then reason="PACKAGE is empty. Set it to owner/name."; echo "$$reason" >&2; exit 1; fi; \
	tab=$$(printf '\t'); \
	releases=$$(gh api --paginate "repos/$$repo/releases?per_page=100" --jq '.[] | [(.id|tostring), .tag_name, .created_at] | @tsv'); \
	if ! plan=$$(printf '%s\n' "$$releases" | awk -F "$$tab" -v tag="$$tag" -v keep="$(KEEP_VERSIONS)" ' \
	  NF < 3 { next } \
	  { n++; id[n] = $$1; name[n] = $$2; created[n] = $$3; if ($$2 == tag) { hits++; cur = n } } \
	  END { \
	    if (hits != 1) exit 2; \
	    keptn = 1; print "keep", id[cur], name[cur]; \
	    while (keptn < keep + 0) { \
	      best = 0; \
	      for (i = 1; i <= n; i++) { \
	        if (i == cur || seen[i] || name[i] ~ /^v/) continue; \
	        if (best == 0 || created[i] > created[best]) best = i; \
	      } \
	      if (best == 0) break; \
	      seen[best] = 1; keptn++; print "keep", id[best], name[best]; \
	    } \
	    for (i = 1; i <= n; i++) if (i != cur && !seen[i] && name[i] !~ /^v/) print "delete", id[i], name[i]; \
	  }'); then \
	  reason="Release $$tag does not exist. Refusing to delete."; \
	  echo "$$reason" >&2; \
	  exit 1; \
	fi; \
	kept=$$(printf '%s\n' "$$plan" | grep -c '^keep ' || true); \
	deleted=$$(printf '%s\n' "$$plan" | grep -c '^delete ' || true); \
	printf '%s\n' "$$plan" | while read -r action id name; do \
	  if [ "$$action" != delete ]; then continue; fi; \
	  case "$$name" in v*) echo "skip $$name: a v* tag is a version, not a build release"; continue ;; esac; \
	  if [ -n "$(DRY_RUN)" ]; then echo "would delete release $$name"; \
	  else \
	    gh api -X DELETE "repos/$$repo/releases/$$id" >/dev/null; \
	    gh api -X DELETE "repos/$$repo/git/refs/tags/$$name" >/dev/null; \
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
	tab=$$(printf '\t'); \
	ids=$$(gh api --paginate "repos/$$repo/actions/artifacts?per_page=100" --jq '.artifacts[] | select(.expired | not) | select((.workflow_run.id // 0) != (env.GITHUB_RUN_ID | tonumber)) | select(.name as $$n | (env.SDLC_KEEP_ARTIFACTS | split(",")) | index($$n) | not) | select((now - (.created_at | fromdateiso8601)) >= (env.SDLC_ARTIFACT_AGE | tonumber)) | [(.id|tostring), .name, (.size_in_bytes|tostring)] | @tsv'); \
	count=0; \
	if [ -n "$$ids" ]; then \
	  printf '%s\n' "$$ids" | while IFS="$$tab" read -r id name size; do \
	    if [ -z "$$id" ]; then continue; fi; \
	    if [ -n "$(DRY_RUN)" ]; then echo "would delete artifact $$id $$name ($$size bytes)"; \
	    else gh api -X DELETE "repos/$$repo/actions/artifacts/$$id" >/dev/null; echo "deleted artifact $$id $$name ($$size bytes)"; fi; \
	  done; \
	  count=$$(printf '%s\n' "$$ids" | grep -c . || true); \
	fi; \
	if [ "$$count" -eq 0 ]; then word=kept; elif [ -n "$(DRY_RUN)" ]; then word=dry-run; else word=deleted; fi; \
	reason="$$count artifact(s) at least $(SDLC_ARTIFACT_AGE)s old, excluding run $$GITHUB_RUN_ID and [$(SDLC_KEEP_ARTIFACTS)]."; \
	if [ -n "$(DRY_RUN)" ]; then reason="$$reason Nothing deleted."; fi; \
	printf '# cleanup-actions-artifacts\n\nStatus: %s\nDeleted: %s\n\n%s\n' "$$word" "$$count" "$$reason" > build/summaries/cleanup-actions-artifacts.md; \
	echo "cleanup-actions-artifacts: $$reason"

endif
