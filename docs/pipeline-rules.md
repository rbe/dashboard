# Pipeline rules

The rules of the pipeline stand once, in the skills `r-project-setup` (the Make contract) and `r-github-pipeline` (the GitHub contract, the publish rules with `AUTO_PUBLISH`, versions, cleanup, and retention). This file does not repeat them. It holds only the facts of this repository and its divergences.

## This repository

| | |
| --- | --- |
| Image | `ghcr.io/rbe/dashboard` |
| Default branch | `master` |
| Toolchain | Node 24 in the image |

Registry login is `make login`. It reads `REGISTRY_USER` and `REGISTRY_TOKEN` and runs `podman login ghcr.io`. The workflow calls that target. It does not log in itself.

`publish-container` pushes every line of `publish-tags`. On the default branch that is `<version>-<run>` and `latest`. A manual publish from any other ref tags the version only and cleanup deletes nothing. `<version>` is the nearest v* tag on the commit, with the leading `v` removed. `<run>` is the GitHub run number. If that tag is missing, the publish fails and does not invent a version. After a successful default-branch push, `cleanup-container-versions` keeps the current published version and exactly one former, the next-lower run number on that line. One published version means it deletes nothing. Cleanup leaves a version that still has `latest` or any tag other than `MAJOR.MINOR.PATCH-<run>`. A missing GHCR package is an empty list. `latest` is a tag on the newest default-branch version, not another package version. A skipped or failed publish deletes nothing.

The app pipeline does not publish a GitHub release. `.github/workflows/publish-client.yml` packs `@rbe/dashboard-client`, creates a GitHub Release, and publishes that package to GitHub Packages on `workflow_dispatch` and tags `client-v*`. The tag must match `client/package.json`. If it does not, the workflow fails and does not invent a version.

## Divergences

Each entry names the shared rule, what differs, and why.

- Rule: `build` saves the image tar and smokes the image. Here: the image smoke checks `/api/dashboard` for `not for git` and the page for `#root`. Why: a laptop and CI both prove the board server before the image tar is saved.
- Rule: `.containerignore` lists `data/`. Here: the image copies `data/dashboard.example.md`, so the ignore lists `data/dashboard.md` and `data/tls` instead of all of `data/`. Why: the example board is part of the image, and the private board is not.
- Rule: `test-changed` selects the tests from the coverage map. Here: `vitest related --run` selects them, as [ADR-0005](adr/ADR-0005.md) says. Why: the workers of Vitest write no V8 coverage per test file.
- Rule: there is one workflow, `.github/workflows/ci.yml`. Here: `.github/workflows/publish-client.yml` packs `@rbe/dashboard-client`, creates a GitHub Release, and publishes it to GitHub Packages. It runs on `workflow_dispatch` and tags `client-v*`. It does not call `make` and does not build the container image. Why: a depending app installs the typed client from GitHub Packages, separate from the image pipeline.
