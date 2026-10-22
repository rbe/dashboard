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

`npm install -g dashboard` does not install this project. That name on the public npm registry already belongs to a different package. Publishing this package there is wired up in the release workflow and stays off until the repository variable `NPM_PUBLISH` is `true` and the `NPM_TOKEN` secret is set.

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
make build
make run
```

Open https://127.0.0.1:4173. `make run` starts the container in the background, and `make stop` stops and removes it. The board file is `data/dashboard.md` in this directory, mounted into the container, and the self-signed certificate is written to `data/tls/` there. `make run PORT=9000` listens on that port.

`make help` lists every target. A description that starts with "Match CI" is a step the GitHub workflows run, so a laptop and CI share one command. Podman is the only container engine.

```sh
make ci
```

`make ci` is what a branch push runs: `make host-checks` (`npm ci`, `npm test`, the Linux binary, and the packed CLI smoke) and then `make ci-image` (one image build, then the smoke of that image). Those commands run inside the Node 24 image. `make macos-binary` is the Apple silicon release binary. It runs on macOS and uses Node 24 already on PATH. It does not install Node.

## GitHub Container Registry

CI, Container, and Release stay separate workflows. The Linux host checks and the image build are reusable workflows, and each event calls each one from a single entry point. Those jobs call the Makefile instead of copying the commands. Triggers, permissions, runner labels, checkout, GHCR login with `podman login`, artifact upload, and `gh release` stay in the workflow files.

On a push to any branch, CI runs the host checks once (`npm ci`, `npm test`, the Linux binary, and a packed CLI smoke). Container builds the image once and smokes that loaded image. These workflows do not also listen for `pull_request`, so a same-repo branch is not tested twice. CI, Container, and Release can each be started by hand with `workflow_dispatch`.

A push to `master` publishes that same image as `ghcr.io/rbe/dashboard:edge` and `ghcr.io/rbe/dashboard:sha-<commit>`. Any other branch, including `main` if it is added later, is built and smoked and not published.

A tag `vX.Y.Z` that matches `package.json` runs the Linux checks once from Release, then the macOS binary, the npm tarball, and the GitHub release. Container builds the image once and publishes `X.Y.Z`, `X.Y`, `X`, and `latest`. Publishing this package to npm stays off until the repository variable `NPM_PUBLISH` is `true`.

```sh
podman pull ghcr.io/rbe/dashboard:latest
```

The published image is `linux/amd64`. Host checks and the image use Node 24. `make build` and `make ci-image` pass that same major into the image. Podman and make do not need Node.js on the host.

## Package

```sh
make test
make linux-binary
```

`make linux-binary` writes the Linux executable CI builds to `build/dashboard`. On macOS, `make macos-binary` writes `build/dashboard-macos` for Apple silicon, using Node 24 already on PATH. Tagging `vX.Y.Z` (matching `package.json`) builds that binary and the npm tarball and attaches both to the GitHub release. The same tag publishes the container image. `make npm-tarball` builds that tarball locally.
