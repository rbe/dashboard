# Pipeline rules

The shared part is the same in every repository. Change it everywhere or nowhere. This repository's facts go under "This repository" and "Divergences".

## Shared rules

The Makefile is the interface. A laptop and CI run the same targets, and a target does the same thing in both places. The workflow calls `make` and moves artifacts. It holds no other logic. Podman is the only container engine. The toolchain runs in a pinned image, so the host needs make, Podman, git, and gh.

`sdlc.mk` at the repository root is the shared makefile. It is byte-identical to the canonical copy. The project Makefile sets `IMAGE`, `PACKAGE`, and `KEEP_VERSIONS`, includes `sdlc.mk`, and defines the project targets.

There is one workflow, `.github/workflows/ci.yml`. Jobs, in order: `setup`, then `build`, `test`, and `docs` beside each other, then `publish-container` (needs `build` and `test`), then `report`. A repository that ships a release asset adds `publish-github`, which also needs `build` and `test`. Each job runs the make target with its name.

`publish-*` runs on a push to the default branch and when `workflow_dispatch` selects it. A tag push does not start a run. Any other branch runs through `report` and does not publish. A manual publish runs `build` and `test` first. In-progress runs are cancelled only off the default branch.

The published version is the nearest `vMAJOR.MINOR.PATCH` tag, without the `v`, plus `-` and the GitHub run number. A default-branch publish also tags `latest`, then keeps that run and the next-lower run number on the same `MAJOR.MINOR.PATCH` line. A manual publish from any other ref tags the version only: it does not move `latest` and cleanup deletes nothing. There is no `edge`, `sha-*`, or bare version tag. No such tag, or a nearer pre-release tag, fails the publish. Cleanup does not delete a GHCR version that still carries `latest` or any tag other than `MAJOR.MINOR.PATCH-<run>`. A missing GHCR package (HTTP 404) is an empty list, so the first publish's cleanup does not fail the job. A skipped or failed publish deletes nothing.

Every upload sets `retention-days`: 1 for intermediates, 14 for `report` and rendered docs. `setup` starts with `cleanup-actions-artifacts`, which deletes this repository's other artifacts once they are an hour old. The current run's artifacts stay, and so do `report` and `docs`.

`report` is last. It still runs when an earlier job fails or is skipped. It writes `build/report/index.md`.

Packages and images contain the tested build only. `.containerignore` keeps out `.claude/`, `.cursor/`, `AGENTS.md`, `CLAUDE.md`, and `docs/`.

## This repository

| | |
| --- | --- |
| Image | `ghcr.io/rbe/dashboard` |
| Default branch | `master` |
| Toolchain | Node 24 in the image |

Registry login is `make login`. It reads `REGISTRY_USER` and `REGISTRY_TOKEN` and runs `podman login ghcr.io`. The workflow calls that target. It does not log in itself.

`publish-container` pushes every line of `publish-tags`. On the default branch that is `<version>-<run>` and `latest`. A manual publish from any other ref tags the version only and cleanup deletes nothing. `<version>` is the nearest v* tag on the commit, with the leading `v` removed. `<run>` is the GitHub run number. If that tag is missing, the publish fails and does not invent a version. After a successful default-branch push, `cleanup-container-versions` keeps the current published version and exactly one former, the next-lower run number on that line. One published version means it deletes nothing. Cleanup leaves a version that still has `latest` or any tag other than `MAJOR.MINOR.PATCH-<run>`. A missing GHCR package is an empty list. `latest` is a tag on the newest default-branch version, not another package version. A skipped or failed publish deletes nothing.

The app pipeline does not publish a GitHub release. `.github/workflows/publish-client.yml` packs `@rbe/dashboard-client`, creates a GitHub Release, and publishes that package to GitHub Packages on `workflow_dispatch` and tags `client-v*`. The tag must match `client/package.json`. If it does not, the workflow fails and does not invent a version. `build` also builds and smokes the Linux binary. That binary is not uploaded and is not a release asset.

## Divergences

Each entry names the shared rule, what differs, and why.

- Rule: `build` saves the image tar and smokes the image. Here: `build` also builds and smokes the Linux binary, and the image smoke checks `/api/dashboard` for `not for git` and the page for `#root`. Why: a laptop and CI both prove the board server and the binary before the image tar is saved. The binary is not a published artifact.
- Rule: `.containerignore` lists `data/`. Here: the image copies `data/dashboard.example.md`, so the ignore lists `data/dashboard.md` and `data/tls` instead of all of `data/`. Why: the example board is part of the image, and the private board is not.
- Rule: there is one workflow, `.github/workflows/ci.yml`. Here: `.github/workflows/publish-client.yml` packs `@rbe/dashboard-client`, creates a GitHub Release, and publishes it to GitHub Packages. It runs on `workflow_dispatch` and tags `client-v*`. It does not call `make` and does not build the container image. Why: a depending app installs the typed client from GitHub Packages, separate from the image pipeline.
