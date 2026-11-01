# Pipeline rules

Locked 30 Oct 2026. Apply to `finanzdesk`, `dashboard`, `ernaehrung`, `erechnung`, and `reelbox`. Keep a project-specific job only when that repo really has that output.

## One workflow

One GitHub workflow file. Jobs, in order, using these names:

- `setup`
- `build`
- `test`
- `npm-package` when the repo packs an npm tarball. Do not call it `npm-tarball`.
- `report`
- `publish-npm` when the repo publishes to the npm registry
- `publish-container` when the repo pushes a container image
- `publish-github` when the repo attaches an artifact to a GitHub release. `erechnung` uses this, not npm or a container.

A job calls the Makefile target with the same name. Do not call `host-checks` from the workflow. Split that into the separate targets the jobs run.

## Artifacts

Pass artifacts between jobs. Do not repeat a job’s work in a later job. A job that can run once its own inputs exist runs beside the others. Web apps do not build an OS-specific package. Delivery is the container image.

`npm-package` needs `build` and `test`, and runs only after both succeed. It packs the built app, not the repository. `publish-github` needs the job that produced the file (`build` or `npm-package`) and downloads that artifact. It does not assemble or pack again. A manual run of `publish-github` still runs that producing job.

Packages and images contain the tested build only. `.gitignore`, `.npmignore`, `.dockerignore`, or `.containerignore` keep out `.claude/`, `AGENTS.md`, `docs/`, and any other instruction or private files. A separate job renders `docs/` as HTML or PDF. That output is not part of the app package or image.

## Runs

A branch push runs through `report` and does not publish. `workflow_dispatch` can start one job on the chosen branch, including a publish job, and that manual publish is allowed to push. Latest major versions of GitHub Actions.

## Report and test

`test` writes a coverage report and test output when the tool can generate them. `report` collects those artifacts and skips when none exist.

## Names

Workflow-level variables hold the container image name and the version, so a rename happens in one place. `finanzdesk` image is `ghcr.io/rbe/orgme`. `npm audit` stays a warning, not a failure.
