# Dashboard

Local markdown dashboard for systems and links. The board is stored in a file on this machine.

## Install

The running app is the container image. This repository does not publish a GitHub release.

### Container

```sh
podman pull ghcr.io/rbe/dashboard:latest
```

The image is `linux/amd64`. `make run` builds it locally and listens on https://127.0.0.1:4173. The certificate is self-signed. The first launch writes it to `data/tls/cert.pem`, and the browser asks before trusting it.

### npm

The command is `dashboard`. Install it from a checkout:

```sh
npm install -g .
```

`npm install -g dashboard` does not install this project. That name on the public npm registry already belongs to a different package. Publishing this package there stays off until the repository variable `NPM_PUBLISH` is `true` and the `NPM_TOKEN` secret is set. A manual run of the `publish-npm` job may publish without that variable.

## Run from a checkout

```sh
npm install
npm start
```

The dev server listens on http://127.0.0.1:5173. `npm run preview` builds and serves the production UI on https://127.0.0.1:4173. That server uses a self-signed certificate, `data/tls/cert.pem` and `data/tls/key.pem`, and creates the pair when it is missing. An expired pair is replaced. `--cert` and `--key` (or `DASHBOARD_TLS_CERT` and `DASHBOARD_TLS_KEY`) select different files.

```sh
dashboard --help
dashboard --port 4173 --file data/dashboard.md
```

`PORT` and `DASHBOARD_FILE` set the same values. The default file is `data/dashboard.md` in the current directory.

## Podman

Podman and make are enough to build and run the app. Node.js and TypeScript are not required on the host; the image installs them and compiles the UI.

```sh
make run
```

Open https://127.0.0.1:4173. `make run` builds the image, starts the container in the background, and `make stop` stops and removes it. The board file is `data/dashboard.md` in this directory, mounted into the container, and the self-signed certificate is written to `data/tls/` there. `make run PORT=9000` listens on that port.

`make help` lists every target. A description that starts with "Match CI" is a job the GitHub workflow runs, so a laptop and CI share one command. Podman is the only container engine. `make ci` runs the jobs through `docs` and `report` on a laptop. It does not publish.

## Pipeline

Job rules are in [docs/pipeline-rules.md](docs/pipeline-rules.md). Podman and make are enough to set the app up. `make setup` checks that a `v*` tag matches `package.json`, installs dependencies with `npm ci` in the Node 24 image, and runs `npm audit` as a warning. It saves `node_modules` for the jobs that follow. The only workflow is `.github/workflows/ci.yml`. Each job runs the Makefile target with the same name. The image name `ghcr.io/rbe/dashboard` and the package version are workflow variables.

```mermaid
flowchart LR
  setup --> build
  setup --> test
  build --> npmPackage["npm-package"]
  test --> npmPackage
  docs["docs"]
  npmPackage --> publishNpm["publish-npm"]
  test --> publishNpm
  build --> publishContainer["publish-container"]
  test --> publishContainer
  setup --> report
  build --> report
  test --> report
  npmPackage --> report
  docs --> report
  publishNpm --> report
  publishContainer --> report
```

A line is that job's `needs` entry. `build` and `test` both wait for `setup`, then run together. `npm-package` waits for both and packs the `dist` tree `build` uploaded. `docs` has no `needs`. It renders `docs/` to HTML beside the other jobs, on every push, and that HTML stays out of the npm package and the image. `publish-npm` and `publish-container` do not wait for each other. `report` is last. It waits for every other job, then collects make output, script output, test results, coverage, and publish results into one artifact. It still runs when a publish job is skipped.

A push to `master` or `main` runs `setup` through `npm-package`, with `docs` beside that chain, then `publish-container`. `publish-npm` joins it when the repository variable `NPM_PUBLISH` is `true`. `report` runs after those publish jobs. Any other branch stops before publish. `report` still runs. A tag `vX.Y.Z` that matches `package.json` uses the same publish rule. Delivery is the container image. This repository does not publish a GitHub release, and it does not upload an npm tarball, image archive, checksums, or source to one. `publish-container` on `master` or `main` pushes `ghcr.io/rbe/dashboard` as `edge` and `sha-<commit>`. On a `vX.Y.Z` tag it pushes `X.Y.Z`, `X.Y`, `X`, and `latest`. `publish-npm` publishes the tarball from `npm-package` when `NPM_PUBLISH` is `true`. A manual run of `publish-npm` may publish without that variable. **Run workflow** starts the one selected job on the chosen branch, and that manual publish may push. Choosing `publish-npm` also runs `setup`, `build`, `test`, and `npm-package`. Choosing `publish-container` also runs `setup`, `build`, and `test`, and that run publishes the image. Choosing `report` runs `setup`, `build`, `test`, `npm-package`, and `docs`, and does not publish. `report` then writes the artifact. A manual `publish-container` on `master` or `main` pushes `:edge` and `:sha-<commit>`. A manual run on any other branch pushes `:sha-<commit>`. A manual run on a `vX.Y.Z` tag pushes the version tags.

The workflow and the image use Node 24. `make image` passes that same major into the image.
