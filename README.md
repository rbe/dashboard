# Dashboard

Local markdown dashboard for systems and links. The board is stored in a file on this machine.

## Install

### macOS binary

GitHub Releases include `dashboard-macos`, one Apple silicon binary. Node.js is not required.

```sh
chmod +x dashboard-macos
xattr -d com.apple.quarantine dashboard-macos
./dashboard-macos
```

Open https://127.0.0.1:4173. The binary is ad-hoc signed, so the first launch may need approval in System Settings → Privacy & Security. The server certificate is self-signed. The first launch writes it to `data/tls/cert.pem`, and the browser asks before trusting it.

### npm

The command is `dashboard`. Install it from a checkout:

```sh
npm install -g .
```

Or from a GitHub release tarball:

```sh
npm install -g https://github.com/rbe/dashboard/releases/download/v1.0.0/dashboard-1.0.0.tgz
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

`make help` lists every target. A description that starts with "Match CI" is a job the GitHub workflow runs, so a laptop and CI share one command. Podman is the only container engine.

```sh
make ci
```

`make ci` is what a branch push runs: `setup`, `build`, `test`, `npm-package`, and `report`. It does not publish. `make build` is the Linux binary and one container image. Those commands run inside the Node 24 image. `make macos-package` is the Apple silicon binary. It runs on macOS and uses Node 24 already on PATH. It does not install Node.

## GitHub Actions

One workflow, `.github/workflows/ci.yml`. Its jobs are `setup`, `build`, `test`, `npm-package`, `macos-package`, `report`, `publish-npm`, `publish-container`, and `publish-github`. Each job runs the Makefile target with the same name and passes artifacts to the jobs that follow. The workflow calls `make`. It does not call `npm ci`, `npm test`, or `npm pack`.

A push to any branch runs through `report` and does not publish. There is no `pull_request` trigger, so a same-repo branch is not tested twice. **Run workflow** starts one selected job on the chosen branch. A manual publish job may push.

A tag `vX.Y.Z` that matches `package.json` runs the same jobs and then publishes. `publish-container` pushes `ghcr.io/rbe/dashboard` as `X.Y.Z`, `X.Y`, `X`, and `latest`. `publish-github` attaches the macOS binary and the npm tarball. `publish-npm` publishes to the npm registry only when the repository variable `NPM_PUBLISH` is `true`. A manual run of `publish-npm` does not need that variable.

A branch push, including `master`, does not push the image. A manual `publish-container` on `master` pushes `ghcr.io/rbe/dashboard:edge` and `:sha-<commit>`. A manual run on any other branch pushes `:sha-<commit>`. The image name and the package version are set once, as workflow variables.

```sh
podman pull ghcr.io/rbe/dashboard:latest
```

The published image is `linux/amd64`. The workflow and the image use Node 24. `make image` passes that same major into the image. Podman and make do not need Node.js on the host.

## Package

```sh
make test
make linux-binary
```

`make linux-binary` writes the Linux executable CI builds to `build/dashboard`. On macOS, `make macos-package` writes `build/dashboard-macos` for Apple silicon, using Node 24 already on PATH. Tagging `vX.Y.Z` (matching `package.json`) builds that binary and the npm tarball and attaches both to the GitHub release. The same tag publishes the container image. `make npm-package` builds that tarball locally.
