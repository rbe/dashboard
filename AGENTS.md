# Agent notes

The Makefile is the interface. A laptop and CI run the same targets. Podman is the only container engine.

## Product

| | |
| --- | --- |
| Name | dashboard |
| Vite dev server | http://127.0.0.1:5173 (`npm start`) |
| Podman HTTPS server | https://127.0.0.1:4173 (`make run`) |
| Data file | `data/dashboard.md` |
| Data env | `DASHBOARD_FILE` |
| API | `/api/dashboard` |
| Smoke needle | `not for git` |
| Linux binary | `build/dashboard` |

`NAME` in the Makefile is the npm package name and the GitHub repository name. Do not commit `data/`.

## Commands

- `npm start` is the Vite dev server.
- `make run` and `make stop` are the Podman HTTPS server. `make image` builds that image.
- `make ci` is a branch push: `setup`, `build`, `test`, `npm-package`, `report`, and `docs`. It does not publish.
- `make setup` installs dependencies, checks a `v*` tag, and runs `npm audit` as a warning.
- `make build` is the Linux binary and one container image.
- `make test` writes a coverage report and test output.
- `make npm-package` packs the built app from `dist` into `build/` and smokes the packed CLI. It does not compile the UI again. It runs only after `build` and `test` succeed.
- `make docs` renders `docs/` to HTML in `build/docs`. It skips when `docs/` has no pages. That HTML is not part of the npm package or the image.
- `make publish-npm` publishes the packed tarball and refuses unless `NPM_PUBLISH=true`.
- `make publish-container` pushes the image saved by `build`.
- `make publish-github` writes the checksums and release notes.
- `make help` lists every target. A description that starts with "Match CI" is a job the GitHub workflow runs.

## Node and containers

Node 24. Linux jobs run inside the Node 24 image, so the host does not need Node. `make publish-npm` is the exception: npm provenance needs the host. Do not add Docker or a second image build.

## Workflows

YAML calls `make`. It does not call `npm ci`, `npm test`, or `npm pack`. One workflow file, `.github/workflows/ci.yml`. Its jobs, in order, are `setup`, `build`, `test`, `npm-package`, `report`, `docs`, `publish-npm`, `publish-container`, and `publish-github`. A job calls the Makefile target with the same name. The workflow does not call `host-checks`.

`build` and `test` both need `setup` and run together. `npm-package` needs `build` and `test`, downloads the `dist` artifact `build` uploaded, and packs that app. `report` needs `test`. `docs` has no `needs` and renders `docs/` to HTML. `.npmignore` and `.containerignore` keep `.claude/`, `AGENTS.md`, `docs/`, and other instruction or private files out of the tarball and the image. `publish-npm`, `publish-container`, and `publish-github` do not need each other. `publish-github` needs `npm-package` and downloads that tarball. A manual `publish-github` still runs `setup`, `build`, `test`, and `npm-package`.

A branch push runs through `report` and does not publish. A `v*.*.*` tag then runs the publish jobs. `workflow_dispatch` runs one selected job on the chosen branch, including a publish job, and that manual publish may push. A manual `publish-npm` or `publish-github` also runs the jobs that produce the tarball. There is no `pull_request` trigger, so a same-repo branch is not tested twice. Fork pull requests do not run CI.

`publish-container` pushes `ghcr.io/rbe/dashboard`. The image name and the package version are workflow-level variables. A branch push, including `master`, does not push the image. A manual `publish-container` on `master` pushes `:edge` and `:sha-<commit>`. A manual run on any other branch pushes `:sha-<commit>`. A `v*` tag pushes the version tags.

`publish-npm` stays off unless the repository variable `NPM_PUBLISH` is `true`, except a manual run of that job. `npm audit` is a warning, not a failure. GHCR login and `gh release` stay in the workflow file. Jobs pass artifacts forward and do not repeat an earlier job's work.

`scripts/workflows.test.mjs` locks this contract. Do not weaken those assertions to make a one-off change pass.
