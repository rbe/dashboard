# Pipeline rules

This repository has one workflow, `.github/workflows/ci.yml`. A job calls the Makefile target with the same name.

## Jobs

In file order:

- `setup`
- `build`
- `test`
- `npm-package`
- `report`
- `docs`
- `publish-npm`
- `publish-container`
- `publish-github`

`build` and `test` both need `setup`, so they run together. `npm-package` needs `build` and `test`, and it runs only after both succeed. It packs the built app from the `dist` artifact.

`report` needs `test`. It collects the coverage report and test output when `test` wrote them. It is skipped when `test` did not set `reports=true`.

`docs` has no `needs`. It renders `docs/` to HTML and runs beside the other jobs. That HTML stays out of the npm package and the image. The render skips when `docs/` has no pages.

`publish-npm`, `publish-container`, and `publish-github` do not need each other. A publish job runs when the jobs it needs have succeeded. It also runs when `report` was skipped and those other jobs succeeded.

- `publish-npm` needs `npm-package`, `test`, and `report`. It publishes the tarball from `npm-package`.
- `publish-container` needs `build`, `test`, and `report`. It pushes the image `build` saved.
- `publish-github` needs `npm-package`, `test`, and `report`. It attaches that tarball to a GitHub release named with the branch or tag (`master`, `main`, or `vX.Y.Z`).

A manual `publish-npm` or `publish-github` also runs `setup`, `build`, `test`, and `npm-package`. A manual `publish-container` also runs `setup`, `build`, and `test`. Those runs leave `report` skipped.

## Artifacts

Pass artifacts between jobs. A later job downloads what an earlier job uploaded.

`setup` uploads `node_modules`. `build` uploads `dist` and the image tar. `test` uploads coverage and test output. `npm-package` uploads the tarball. `docs` uploads the HTML when the render wrote files.

`.npmignore` and `.containerignore` keep `.claude/`, `AGENTS.md`, `docs/`, and other instruction or private files out of the package and the image.

## Runs

A push to `master` or `main` runs `publish-container` and `publish-github` after the jobs they need, and runs `publish-npm` when the repository variable `NPM_PUBLISH` is `true`. Any other branch runs through `report` and does not publish. `docs` runs on every push. A `v*.*.*` tag uses the same publish rule when the tag matches `package.json`. A manual run of `publish-npm` may publish without `NPM_PUBLISH`.

`workflow_dispatch` starts the one selected job, including a publish job, and that manual publish may push. Choosing `report` alone does not run `test`, so `report` stays skipped.

There is no `pull_request` trigger, so a same-repo branch is not run twice.

## Names

`IMAGE_NAME` is `ghcr.io/rbe/dashboard`. `VERSION` is the `package.json` version. Both are workflow-level variables. The workflow and the image use Node 24. `npm audit` is a warning, not a failure.

`publish-container` on `master` or `main` pushes `edge` and `sha-<commit>`. On a `vX.Y.Z` tag it pushes `X.Y.Z`, `X.Y`, `X`, and `latest`. A manual run on any other branch pushes `sha-<commit>`. A manual run on a `vX.Y.Z` tag pushes those version tags.
