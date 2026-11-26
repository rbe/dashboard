# The Makefile of a project

## Sample

```make
SETUP_CMD = npm ci
BUILD_CMD = npm run build
TEST_CMD = npm test
FORMAT_CMD = npm exec -- prettier --check .
LINT_CMD = npm exec -- eslint .
INTEGRATION_CMD = npm run integration
RENDER_DOCS = 1
DOCS_CMD = node scripts/render-docs.mjs docs build/docs
PUBLISH_IMAGE = 1
include .claude/skills/r-project-setup/project.mk

# Project targets. A target of the Make contract is not defined again here.
```

Make reads `RENDER_DOCS` and `PUBLISH_IMAGE` while it parses `project.mk`. Set them above the include.

## Targets

| Target | When | What it does |
| --- | --- | --- |
| `doctor` | Always | Checks that this machine has Make, Git, and Podman |
| `podman-start` | Always | Starts the Podman machine on macOS, and creates it when none exists |
| `setup` | Always | Runs `doctor` first, then `toon` when `r-record` is installed, then `SETUP_CMD`. A failed `doctor` stops `setup` |
| `build` | Always | Produces the artifact. The Gradle build runs here |
| `test` | Always | Runs the unit tests |
| `editorconfig` | Always | Checks the tree with editorconfig-checker |
| `format` | Always | Checks the files with the one formatter |
| `format-fix` | Always | Rewrites the files with that formatter |
| `lint` | Always | Runs the one linter |
| `integration` | Always | Runs the one integration entry |
| `coverage` | Always | Writes the diff-cover report of the lines that this change touched |
| `test-changed` | Always | Runs the tests that cover the files in the diff |
| `old-board` | Always | Prints each path of the old board that exists, and a `docs/ROADMAP.md` in the old line form. Fails when one of these nine checks finds something |
| `skills-install` | Always | Installs the skills that `apm.yml` names. `DRY_RUN=1` prints the plan and changes nothing |
| `skills-update` | Always | Updates the skills to the version that `apm.yml` allows. `DRY_RUN=1` prints the plan and changes nothing |
| `apm` | Always | Runs any other APM command: `make apm ARGS='...'` |
| `py` | Always | Runs Python in Podman: `make py ARGS='...'` |
| `r-project-report` | When that skill is installed | Writes `build/project-report.md` |
| `docs` | Only when the repository renders docs | Runs the renderer |
| `login` | Only when an image is published | Reads `REGISTRY_USER` and `REGISTRY_TOKEN` and runs `podman login` on `REGISTRY` |

`build`, `test`, and `docs` are stubs. If the command variable is empty, the target fails and names the variable.

`help` lists `setup`, `build`, `test`, `test-changed`, and `r-project-report`. It lists `docs` and `login` only when those targets exist.

## Variables

| Variable | Meaning |
| --- | --- |
| `HELP_LEAD` | The first line of `make help`. `project.mk` has a default |
| `SETUP_CMD` | How this project resolves dependencies. Empty fails `setup` |
| `BUILD_CMD` | How this project produces the artifact. Empty fails `build` |
| `TEST_CMD` | How this project runs the unit tests. Empty fails `test` |
| `FORMAT_CMD` | The one formatter in check mode. It changes no file. Empty fails `format` |
| `FORMAT_FIX_CMD` | The same formatter in write mode. Empty fails `format-fix` |
| `LINT_CMD` | The one linter. Empty fails `lint` |
| `INTEGRATION_CMD` | The one integration entry. Empty fails `integration` |
| `COVERAGE_CMD` | Writes `build/coverage/diff.md` and the coverage map that `test-changed` reads. Empty fails `coverage` |
| `TEST_CHANGED_CMD` | Runs the tests that cover the diff. The selection is coverage, not a hand-kept list. Empty fails `test-changed` |
| `PROJECT_REPORT_CMD` | Writes `build/project-report.md`. `report.mk` in `r-project-report` sets it when that skill is installed and the project did not set it. Empty fails `r-project-report` |
| `RENDER_DOCS` | `1` when this repository renders docs. Otherwise there is no `docs` target |
| `DOCS_CMD` | The renderer. Empty fails `docs` |
| `PUBLISH_IMAGE` | `1` when an image is published. Otherwise there is no `login` target |
| `REGISTRY` | The registry host of `login`. Default `ghcr.io` |
| `DEFAULT_BRANCH` | The default branch. Make finds it: the origin default branch, else `main`, else `master` |
| `PYTHON_IMAGE` | The image of `$(PYTHON)`. Default `docker.io/library/python:3.13-slim` |
| `APM_IMAGE` | The image that runs APM. It has git and Python. Default `docker.io/library/python:3.13` |
| `APM_VERSION` | The APM version of `skills-install` and `skills-update`. Default `0.36.1` |
| `DIFF_COVER_IMAGE` | The image that runs diff-cover. It has git and Python. Default `docker.io/library/python:3.13` |
| `PODMAN_NET_ARGS` | Extra `podman` arguments of a container that reads the network (APM, the GitHub CLI, and the `pip` runs of diff-cover and coverage), such as a CA mount behind a proxy |

The language skill names the tool of `FORMAT_CMD`, `LINT_CMD`, `COVERAGE_CMD`, and `TEST_CHANGED_CMD`. `r-project-report` ships the test selection for Python, Node, and the JVM.

## Makefiles of this skill

| File | Provides |
| --- | --- |
| `project.mk` | `help`, and the includes of every file below |
| `contract.mk` | `setup`, `build`, `test`, the quality targets, `r-project-report`, and `docs` and `login` when the variables say so |
| `doctor.mk` | `doctor` |
| `skills.mk` | `skills-install`, `skills-update`, `apm` |
| `old-board.mk` | `old-board` |
| `test-changed.mk` | `test-changed` |
| `podman-python.mk` | `$(PYTHON)` and `py` |
| `tools.mk` | The images and versions of editorconfig-checker, diff-cover, and APM |

The `sdlc.mk` of `r-github-pipeline` includes the same `contract.mk`, `doctor.mk`, `skills.mk`, `old-board.mk`, and `test-changed.mk`. The targets stay when a project changes from `project.mk` to `sdlc.mk`. A repository on `sdlc.mk` defines its own project targets.

`project.mk` marks each standard target `.PHONY`. Without that mark, a `build/` directory satisfies `build`.

`project.mk` sets `.DEFAULT_GOAL` to `help` after the files that it includes. `podman-python.mk`, `tools.mk`, `test-changed.mk`, the `index.mk` of `r-record`, and the `report.mk` of `r-project-report` set the same goal.

## `make doctor`

`doctor` checks GNU Make 3.81 or newer, Git, `podman info`, and, when the project has a workflow, the remote `origin`. Each check prints `ok` or `FAIL` with the fix. A `FAIL` stops the target with exit 1. On macOS a stopped Podman machine fails `podman info`, and the fix line says `make podman-start`. The `setup` of the Node and Gradle templates of `r-github-pipeline` also runs `make doctor` first.

## `make coverage` and `make test-changed`

The diff is the branch against the default branch. On the default branch the diff is empty, so the report has no line and `test-changed` runs no test. `coverage` runs `git add -N .`, so each new file is marked in the index and counts as changed.
