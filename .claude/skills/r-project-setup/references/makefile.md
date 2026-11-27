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
PUBLISH_IMAGE = 1
include .claude/skills/r-project-setup/project.mk

# Project targets. A target of the Make contract is not defined again here.
```

Make reads `RENDER_DOCS` and `PUBLISH_IMAGE` while it parses `project.mk`. Set them above the include.

## Targets

| Target | When | What it does |
| --- | --- | --- |
| `doctor` | Always | Checks that this machine has Make, Git, and Podman. With `TOOLS=host`, it checks `python3` in place of Podman |
| `host-tools` | Always | Installs the pinned tools of host mode into `build/host-tools`: ruff, coverage, diff-cover, and APM with `pip` into a venv, and editorconfig-checker with `go install`. With `TOOLS=host`, `setup` runs it |
| `git-hooks` | Always | Installs the git hook `pre-push`. `setup`, `gates`, and `test-changed` run it |
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
| `check-docs` | Always | Fails when a skill text names a path under `skills/r-*/` or `.claude/skills/r-*/` that does not exist, or a `make` target that no makefile defines. `test` runs it first |
| `old-board` | Always | Prints each path of the old board that exists, and a `docs/ROADMAP.md` in the old line form. Fails when one of these nine checks finds something |
| `skills-install` | Always | Installs the skills that `apm.yml` names. `DRY_RUN=1` prints the plan and changes nothing |
| `skills-update` | Always | Updates the skills to the version that `apm.yml` allows. `DRY_RUN=1` prints the plan and changes nothing |
| `apm` | Always | Runs any other APM command: `make apm ARGS='...'` |
| `py` | Always | Runs Python in Podman: `make py ARGS='...'` |
| `project-report` | When that skill is installed | Writes `build/project-report.md` |
| `docs` | Only when the repository renders docs | Runs `DOCS_CMD`. The default writes one HTML file for each Markdown file under `docs/`, an `index.html`, and `build/summaries/docs.md` |
| `login` | Only when an image is published | Reads `REGISTRY_USER` and `REGISTRY_TOKEN` and runs `podman login` on `REGISTRY` |

`build` and `test` are stubs. If the command variable is empty, the target fails and names the variable.

`help` lists `setup`, `build`, `test`, `test-changed`, and `project-report`. It lists `docs` and `login` only when those targets exist.

`help` prints the targets in groups. The groups are `Gates`, `Project`, `Board`, `Delivery`, and `Tools`, in that order, and `HELP_GROUPS` holds the order. In a makefile, the line `# help-group: <Name>` puts the targets that follow it in that group. The first line of each file starts in `Project`, so a target of the product Makefile is listed there. A group that `HELP_GROUPS` does not name prints after those, and a group with no target prints no heading. A makefile of this collection that defines a target with a `##` comment has the marker before its first target.

## Variables

| Variable | Meaning |
| --- | --- |
| `HELP_LEAD` | The first line of `make help`. `project.mk` has a default |
| `HELP_GROUPS` | The groups of `make help`, in print order. Default `Gates Project Board Delivery Tools` |
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
| `DOCS_CMD` | The renderer. Empty means `scripts/render_docs.py` of `r-project-setup`, run with `$(PYTHON)`. Options go in `DOCS_OPTIONS`, such as `--lang de` |
| `DOCS_SOURCE`, `DOCS_OUT` | The input and output directory of the shared renderer. Defaults `docs` and `build/docs` |
| `PUBLISH_IMAGE` | `1` when an image is published. Otherwise there is no `login` target |
| `REGISTRY` | The registry host of `login`. Default `ghcr.io` |
| `DEFAULT_BRANCH` | The default branch. Make finds it: the origin default branch, else `main`, else `master` |
| `PYTHON_IMAGE` | The image of `$(PYTHON)`. Default `docker.io/library/python:3.13-slim` |
| `APM_IMAGE` | The image that runs APM. It has git and Python. Default `docker.io/library/python:3.13` |
| `APM_VERSION` | The APM version of `skills-install` and `skills-update`. Default `0.36.1` |
| `DIFF_COVER_IMAGE` | The image that runs diff-cover. It has git and Python. Default `docker.io/library/python:3.13` |
| `PODMAN_NET_ARGS` | Extra `podman` arguments of a container that reads the network (APM, the GitHub CLI, and the `pip` runs of diff-cover and coverage), such as a CA mount behind a proxy |
| `TOOLS` | Where Make runs a tool. `podman`, the default, runs it in its image. `host` runs it from `PATH`, with `build/host-tools/bin` first, for a machine without Podman, such as a cloud session. The image targets still need Podman |
| `HOST_TOOLS_DIR` | Where `host-tools` installs. Default `build/host-tools` |
| `RUFF` | Runs ruff, the formatter and linter of Python. A Python project uses it in `FORMAT_CMD` and `LINT_CMD` |
| `COVERAGE_PYTHON` | Runs a Python script with the package coverage. A Python project uses it in `COVERAGE_CMD` |
| `BOARD_FILES` | The files that the close of a task changes. The pre-push hook accepts a commit that differs from `build/gates.ok` only in these files. Default `docs/history/ docs/ROADMAP.md docs/proposals/` |

The language skill names the tool of `FORMAT_CMD`, `LINT_CMD`, `COVERAGE_CMD`, and `TEST_CHANGED_CMD`. `r-project-report` ships the test selection for Python, Node, and the JVM.

## Makefiles of this skill

| File | Provides |
| --- | --- |
| `project.mk` | `help`, and the includes of every file below |
| `help.mk` | `HELP_GROUPS` and `HELP_LIST`, the awk command that `help` runs. `project.mk` includes it, and `sdlc.mk` includes `project.mk` |
| `contract.mk` | `setup`, `build`, `test`, the quality targets, `project-report`, and `docs` and `login` when the variables say so |
| `doctor.mk` | `doctor` |
| `skills.mk` | `skills-install`, `skills-update`, `apm` |
| `old-board.mk` | `old-board` |
| `test-changed.mk` | `test-changed` |
| `check-docs.mk` | `check-docs` |
| `podman-python.mk` | `$(PYTHON)` and `py` |
| `tools.mk` | The images and versions of editorconfig-checker, ruff, coverage, diff-cover, and APM, the host forms of these tools, `BOARD_FILES`, and `host-tools` |

The `sdlc.mk` of `r-github-pipeline` includes the same `contract.mk`, `doctor.mk`, `skills.mk`, `old-board.mk`, `test-changed.mk`, and `check-docs.mk`. The targets stay when a project changes from `project.mk` to `sdlc.mk`. A repository on `sdlc.mk` defines its own project targets.

`project.mk` marks each standard target `.PHONY`. Without that mark, a `build/` directory satisfies `build`.

`project.mk` sets `.DEFAULT_GOAL` to `help` after the files that it includes. `podman-python.mk`, `tools.mk`, `test-changed.mk`, the `index.mk` of `r-record`, and the `report.mk` of `r-project-report` set the same goal.

## `make doctor`

`doctor` checks GNU Make 3.81 or newer, Git, `podman info`, and, when the project has a workflow, the remote `origin`. Each check prints `ok` or `FAIL` with the fix. A `FAIL` stops the target with exit 1. On macOS a stopped Podman machine fails `podman info`, and the fix line says `make podman-start`. The `setup` of the Node and Gradle templates of `r-github-pipeline` also runs `make doctor` first.

## `make coverage` and `make test-changed`

The diff is the branch against the default branch. On the default branch the diff is empty, so the report has no line and `test-changed` runs no test. Before `COVERAGE_CMD`, `coverage` writes `build/change.diff`, outside `build/coverage/`, which a coverage tool such as Vitest may clean, with `CHANGE_DIFF` of `tools.mk`. Each untracked file that git does not ignore counts as changed, and the recipe stages nothing. `DIFF_BASE` is the base of that diff and of `test-changed`. A `COVERAGE_CMD` does not write the diff again.
