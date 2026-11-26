# Pipeline rules

The shared part is the same in every repository. Change it everywhere or nowhere. This repository's facts go under "This repository" and "Divergences". The Node 24 line is the Node template only. A Gradle project uses the JDK in its template. A project diverges by toolchain and writes that down.

## Shared rules

The Make contract is the r-project-setup skill. Make is the only interface. A person or an agent does the work through Make. `help` is the default goal. A target does the same thing on a laptop and in CI. The required targets are `setup`, `build`, `test`, `editorconfig`, `format`, `lint`, `integration`, and `coverage`. `test-changed` comes with the include. It is not a CI target. Set `TEST_CHANGED_CMD` before the include. Add `docs` only when this repository renders docs, and `login` when it publishes an image. `format` and `lint` run the one existing formatter and the one existing linter the language skill names. `coverage` writes `build/coverage/diff.md` for the lines this change touched. It does not apply a repository-wide percentage. Gradle, npm, Podman, python, and tar run inside those targets. CI runs those same targets.

The GitHub contract is the r-github-pipeline skill. Podman is the only container engine. The toolchain runs in a pinned image, so the host needs make, Podman, and git. The GitHub CLI runs in Podman, in the image of `make gh-image`. The Node template pins Node 24. A Gradle project uses the JDK in its template. A project diverges by toolchain and writes that down. The project Makefile sets `IMAGE`, `PACKAGE`, and `KEEP_VERSIONS`, includes `.claude/skills/r-github-pipeline/sdlc.mk` before any target, and defines the project targets. That include already provides `help`, so this repository leaves `project.mk` out. There is no root copy of `sdlc.mk`.

There is one workflow, `.github/workflows/ci.yml`. A step is a checkout, an artifact upload or download, or `run: make <target>`. Jobs, in order: `setup`, then `build` and `test` beside each other (and `docs`, only when the repository renders docs), then `publish-container` (needs `build` and `test`), then `report`. A repository that releases a JAR adds `publish-github`, which also needs `build` and `test`. Each job runs the make target with its name.

`publish-*` runs on a push to the default branch and when `workflow_dispatch` selects it. A tag push does not start a run. Any other branch runs through `report` and does not publish. A manual publish runs `build` and `test` first. In-progress runs are cancelled only off the default branch.

The published version is the nearest `vMAJOR.MINOR.PATCH` tag, without the `v`, plus `-` and the GitHub run number. A default-branch publish also tags `latest`, then keeps that run and the next-lower run number on the same `MAJOR.MINOR.PATCH` line. A manual publish from any other ref tags the version only: it does not move `latest` and cleanup deletes nothing. There is no `edge`, `sha-*`, or bare version tag. No such tag, or a nearer pre-release tag, fails the publish. Cleanup does not delete a GHCR version that still carries `latest` or any tag other than `MAJOR.MINOR.PATCH-<run>`. A missing GHCR package (HTTP 404) is an empty list, so the first publish's cleanup does not fail the job. A skipped or failed publish deletes nothing.

Every upload sets `retention-days`: 1 for intermediates, 14 for `report` and rendered docs. `setup` starts with `cleanup-actions-artifacts`, which deletes this repository's other artifacts once they are an hour old. The current run's artifacts stay, and so do `report` and `docs`.

`report` is last. It still runs when an earlier job fails or is skipped. It writes `build/report/index.md`.

Packages and images contain the tested build only: a binary or a container image. `.containerignore` keeps out `.claude/`, `CLAUDE.md`, `docs/`, and `data/`. Example data ships only from `examples/` when the path and the name say it is an example.

## This repository

Replace each bracket with a fact of this repository.

| | |
| --- | --- |
| Image | `ghcr.io/[owner]/[name]` |
| Default branch | [the default branch] |
| Toolchain | [the toolchain and the image of this project] |

## Divergences

Each entry names the shared rule, what differs, and why. A toolchain difference belongs here.

- Rule: [the shared rule]. Here: [what differs]. Why: [the reason].
