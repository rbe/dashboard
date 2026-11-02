# Pipeline rules

This repository has one workflow, `.github/workflows/ci.yml`. A job calls the Makefile target with the same name.

## Jobs

In file order:

- `setup`
- `build`
- `test`
- `docs`
- `publish-container`
- `report`

`build`, `test`, and `docs` each need `setup`, so those three run together. `docs` needs only `setup`. It renders `docs/` to HTML. That HTML stays out of the image. The render skips when `docs/` has no pages.

`publish-container` needs `build` and `test`. It runs only after both succeed. It pushes the image `build` saved. It runs on a push to `master` or `main`, and when `workflow_dispatch` selects it. Any other branch skips it.

Delivery is the container image. This repository does not publish a GitHub release.

`report` is the last job. It needs `setup`, `build`, `test`, `docs`, and `publish-container`. It still runs when `publish-container` succeeds, fails, or is skipped. The report artifact holds make output, script output, test results, coverage, and publish results: image tags, what was pushed or skipped, and why. Open `index.md` in that artifact.

A manual `publish-container` also runs `setup`, `build`, and `test`, and that run publishes the image. A manual `report` runs `setup`, `build`, `test`, and `docs`, and does not publish. `report` runs after the selected job.

## Artifacts

Pass artifacts between jobs. A later job downloads what an earlier job uploaded.

`setup` uploads `node_modules`. `build` uploads `dist` and the image tar. `test` uploads coverage and test output. `docs` uploads the HTML when the render wrote files. Each of those jobs also uploads its log and summary for `report`. `publish-container` downloads the image tar. `report` uploads one `report` artifact. The image tar stays a job artifact. It is not a release asset.

`.npmignore` and `.containerignore` keep `.claude/`, `AGENTS.md`, `docs/`, and other instruction or private files out of the package and the image.

## Runs

A push to `master` or `main` runs `publish-container` after `build` and `test`. Any other branch skips `publish-container` and still runs `report`. `docs` runs on every push, beside `build` and `test`. A `v*.*.*` tag push runs through `report` and does not publish. `workflow_dispatch` starts the one selected job. Choosing `publish-container` publishes. `report` still runs after that job, including when publish is skipped or fails.

There is no `pull_request` trigger, so a same-repo branch is not run twice.

## Names

`IMAGE_NAME` is `ghcr.io/rbe/dashboard`. `VERSION` is the `package.json` version. Both are workflow-level variables. The workflow and the image use Node 24. `npm audit` is a warning, not a failure.

`publish-container` on `master` or `main` pushes `edge` and `sha-<commit>`. A manual run on any other branch pushes `sha-<commit>`. A manual run on a `vX.Y.Z` tag pushes `X.Y.Z`, `X.Y`, `X`, and `latest`. A tag push does not run the job.
