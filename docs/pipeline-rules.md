# Pipeline rules

This repository has one workflow, `.github/workflows/ci.yml`. A job calls the Makefile target with the same name.

## Jobs

In file order:

- `setup`
- `build`
- `test`
- `npm-package`
- `docs`
- `publish-npm`
- `publish-container`
- `report`

`build` and `test` both need `setup`, so they run together. `npm-package` needs `build` and `test`, and it runs only after both succeed. It packs the built app from the `dist` artifact.

`docs` has no `needs`. It renders `docs/` to HTML and runs beside the other jobs. That HTML stays out of the npm package and the image. The render skips when `docs/` has no pages.

`publish-npm` and `publish-container` do not need each other. A publish job runs when the jobs it needs have succeeded.

- `publish-npm` needs `npm-package` and `test`. It publishes the tarball from `npm-package` to the npm registry when `NPM_PUBLISH` is `true`.
- `publish-container` needs `build` and `test`. It pushes the image `build` saved.

There is no `publish-github` job. Delivery is the container image. This repository does not publish a GitHub release, and it does not upload an npm tarball, image archive, checksums, or source to one.

`report` is the last job. It needs `setup`, `build`, `test`, `npm-package`, `docs`, `publish-npm`, and `publish-container`. It runs when those jobs succeed, fail, or are skipped, so a branch push that skips publish still produces a report. The report artifact holds make output, script output, test results, coverage, and publish results: image tags, what was pushed or skipped, and why. Open `index.md` in that artifact.

A manual `publish-npm` also runs `setup`, `build`, `test`, and `npm-package`. A manual `publish-container` also runs `setup`, `build`, and `test`, and that run publishes the image. A manual `report` runs `setup`, `build`, `test`, `npm-package`, and `docs`, and does not publish. `report` runs after the selected job.

## Artifacts

Pass artifacts between jobs. A later job downloads what an earlier job uploaded.

`setup` uploads `node_modules`. `build` uploads `dist` and the image tar. `test` uploads coverage and test output. `npm-package` uploads the tarball. `docs` uploads the HTML when the render wrote files. Each of those jobs also uploads its log and summary for `report`. `report` uploads one `report` artifact. The image tar and the npm tarball stay job artifacts. They are not release assets.

`.npmignore` and `.containerignore` keep `.claude/`, `AGENTS.md`, `docs/`, and other instruction or private files out of the package and the image.

## Runs

A push to `master` or `main` runs `publish-container` after the jobs it needs, and runs `publish-npm` when the repository variable `NPM_PUBLISH` is `true`. Any other branch stops before publish. `docs` runs on every push. `report` runs on every push, after publish, including when publish is skipped. A `v*.*.*` tag uses the same publish rule when the tag matches `package.json`. A manual run of `publish-npm` may publish without `NPM_PUBLISH`.

`workflow_dispatch` starts the one selected job. Choosing `publish-container` publishes. `report` still runs after that job and records what the run did.

There is no `pull_request` trigger, so a same-repo branch is not run twice.

## Names

`IMAGE_NAME` is `ghcr.io/rbe/dashboard`. `VERSION` is the `package.json` version. Both are workflow-level variables. The workflow and the image use Node 24. `npm audit` is a warning, not a failure.

`publish-container` on `master` or `main` pushes `edge` and `sha-<commit>`. On a `vX.Y.Z` tag it pushes `X.Y.Z`, `X.Y`, `X`, and `latest`. A manual run on any other branch pushes `sha-<commit>`. A manual run on a `vX.Y.Z` tag pushes those version tags.
