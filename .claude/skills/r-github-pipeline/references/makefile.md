# The Makefile of a project that includes sdlc.mk

The project Makefile sets variables, includes `sdlc.mk` before any target, and then defines the project targets.

```make
IMAGE ?= ghcr.io/owner/name
PACKAGE ?= owner/name
KEEP_VERSIONS ?= 2
SETUP_CMD = set -eu; ...; printf '\# setup\n\n...\n' > build/summaries/setup.md
BUILD_CMD = ...
TEST_CMD = ...
include .claude/skills/r-github-pipeline/sdlc.mk
```

The project sets the command variables of `r-project-setup` above the include. It defines no contract target again. A `#` inside a command variable is written `\#`, because Make reads an unescaped `#` as a comment. A command variable that needs the summary of a job writes it to `build/summaries/<job>.md`.

## Variables to set before the include

| Variable | Meaning |
| --- | --- |
| `IMAGE` | `ghcr.io/owner/name`, no tag |
| `PACKAGE` | GitHub `owner/name`. The default is `GITHUB_REPOSITORY` |
| `KEEP_VERSIONS` | The number of versions to keep, including the version just published. The default is 2 |
| `SDLC_JOBS` | The jobs that the pipeline report lists. Add `publish-github` when that job exists |
| `SDLC_CI` | The targets that `ci` runs, in order. The default is `setup build editorconfig format lint test integration coverage docs report`. Remove `docs` when there is no docs target |
| `SDLC_KEEP_ARTIFACTS` | The artifact names that the hourly cleanup does not delete. The default is `report,docs` |
| `SMOKE_PATH`, `SMOKE_NEEDLE`, `SMOKE_PAGE_NEEDLE` | In `templates/Makefile.node`: the API path and its needle, and the text that the page at `/` must hold. The defaults are `/api/health`, `ok`, and `id="root"`. An empty `SMOKE_PAGE_NEEDLE` turns the page check off |
| `PORT`, `HOST_PORT` | In `templates/Makefile.node`: the port inside the container, and the port of the host that `make run` binds. `HOST_PORT` stays above 1024 and `run` fails below it |
| `CI_BOARD_FILES` | The board files that `ci-scope` counts. A path that ends in `/` is a directory. The default is `docs/history/ docs/ROADMAP.md docs/proposals/` |
| `HELP_LEAD` | The first line of `make help` |
| `GH_BASE_IMAGE`, `GH_VERSION` | The base image and the release of the GitHub CLI image |
| `OWNER`, `NAME` | The GitHub owner and the repository name. `ci-status` passes them as `-R owner/name`, and `pull-request` and `pull-request-merge` put them in the REST route, because the image has no Git |

## Recipe helpers

- `$(call SDLC_LOG,job,_job)` writes the output of `_job` to `build/logs/job.log`. If `_job` fails, it writes a failed summary. `_job` is the real recipe. The goal name contains no comma.
- If a recipe must not run under `make -n`, it calls `$(THIS_MAKE)`, not `$(MAKE)`. Make executes a recipe line that contains `$(MAKE)` during a dry run, and that line could push an image.
- `ci` calls `$(MAKE)`, so that `make -n ci` goes through the child targets. `ci` does not publish.
- `$(GH)` runs the GitHub CLI in the image that `make gh-image` builds. The token is `GH_TOKEN` or `GITHUB_TOKEN` of the environment, on a laptop and in CI.
- The cleanup recipes list with `gh api --jq`. An `awk` plan inside the cleanup recipe selects the versions to keep.

## Targets of sdlc.mk

| Target | Contract |
| --- | --- |
| `help` | The default goal. It lists every target that has a `##` comment, in the groups of `help.mk` in `r-project-setup`. One include is sufficient, because `sdlc.mk` defines `help` |
| `version` | Prints `MAJOR.MINOR.PATCH-run` from `git describe`. `PRINT=tag` prints the `vX.Y.Z` tag. Fails when there is no strict tag, when a pre-release tag is nearer, or when `GITHUB_RUN_NUMBER` is not set |
| `ci` | Runs `SDLC_CI` in order. Does not publish |
| `report` | Writes `build/report/index.md` from logs, summaries, and `JOB_RESULT_*` |
| `check-tag` | Run it before the tag is pushed, as `make check-tag TAG=vX.Y.Z`. Fails unless `TAG` is `vMAJOR.MINOR.PATCH`, does not exist, is newer than every strict `v*` tag, and `HEAD` is the tip of the default branch |
| `publish-tags` | Prints the version. Prints `latest` only when the ref is the default branch or `GITHUB_REF` is not set |
| `gh-image` | Builds the image of the GitHub CLI, one time |
| `ci-status` | Prints the result of the CI run for `HEAD`, or for `SHA=<sha>`. Fails when the run failed, did not finish, or does not exist. `WAIT=1` waits for the end |
| `ci-scope` | Prints `board-only=true` and writes it to `GITHUB_OUTPUT` when the push changes only `CI_BOARD_FILES` and `make ci-status` passes for the base commit. Else prints `board-only=false`. The base is `CI_BEFORE`, else the merge base with `origin/DEFAULT_BRANCH`. A missing base, another event than `push`, or any other file gives `false`. Writes the reason to `build/summaries/ci-scope.md` |
| `pull-request` | Opens a pull request from the current branch to `DEFAULT_BRANCH`. `TITLE` and `BODY` are optional. Prints the open one when it exists. Uses `gh api` REST routes only |
| `pull-request-merge` | Merges the pull request of the current branch when all check runs of its head commit passed. No check run, or one that did not pass, stops the merge. `WAIT=1` waits for the checks. Uses `gh api` REST routes only |
| `cleanup-container-versions` | On the default branch, keeps one version and the next-lower run on the same `MAJOR.MINOR.PATCH` line. The kept version is `PUBLISHED_TAG`, else the content of `build/publish-version.txt`, else the newest rolling version by `created_at`. Needs no git tag. A missing package, or a list with no rolling version, is an empty list. Does not delete `latest` or a tag that is not `MAJOR.MINOR.PATCH-<run>`. A given tag that is not exactly one version stops the target, and the message names its source. In CI, off the default branch, deletes nothing |
| `cleanup-github-releases` | On the default branch, keeps one release and the next-lower run, chosen as in `cleanup-container-versions`. Needs no git tag. Does not delete a name that is not `MAJOR.MINOR.PATCH-<run>`. A list with no rolling release deletes nothing. In CI, off the default branch, deletes nothing |
| `cleanup-actions-artifacts` | Deletes the artifacts of this repository that are older than one hour, except `report`, `docs`, and the artifacts of this run |

`DRY_RUN=1` makes each cleanup print what it would delete. The cleanup then only reads, so it is safe against the real API. A cleanup runs at any time, with or without `DRY_RUN=1` and with or without a git tag. Without `DRY_RUN=1` it deletes, also on a laptop.

## Targets of container.mk

`container.mk` provides `image`, `image-ci`, and `publish-container` for every project that includes `sdlc.mk`, the Node and Gradle templates included. The project changes them through variables: `IMAGE_BUILD_ARGS`, `SMOKE_CMD`, `CONTAINERFILE`, `IMAGE_CONTEXT`, `IMAGE_PREPARE`, and `PUBLISH_PREPARE`. The Node template sets `SMOKE_CMD` to a curl check of the running image, and its `BUILD_CMD` ends with `make image-ci`. The Gradle template builds the image from the tested JAR: `IMAGE_PREPARE` copies the JAR into `build/image-context`, and `PUBLISH_PREPARE` runs `make image` before the push.

## Targets that the project defines

- `setup`, `build`, and `test` are required names of the `r-project-setup` contract. The project sets `SETUP_CMD`, `BUILD_CMD`, and `TEST_CMD`, and defines none of these targets. `docs` exists only when the project sets `RENDER_DOCS = 1` and `DOCS_CMD`. `login` exists only when the project sets `PUBLISH_IMAGE = 1`.
- `login` is the target of `contract.mk`. It reads `REGISTRY_USER` and `REGISTRY_TOKEN` and runs `podman login` for `REGISTRY`, which is `ghcr.io` by default. The publish job runs `make login` before `make publish-container`.
- `publish-container` pushes every line of `make publish-tags` and writes the version to `build/publish-version.txt`. On the default branch the lines are the version and `latest`. From any other ref the only line is the version, and the cleanup targets exit and delete nothing.
- `publish-github` exists when the project releases a JAR or a binary.
- In a Gradle project, `make build` runs Gradle: `BUILD_CMD` in the template runs `$(GRADLE) assemble`.
- A command for the laptop only gets its own name, for example `dev` or `verify`.
