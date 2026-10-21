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

Podman and make are enough. Node.js and TypeScript are not required on the host; the image installs them and compiles the UI.

```sh
make build
make run
```

Open https://127.0.0.1:4173. `make run` starts the container in the background, and `make stop` stops and removes it. The board file is `data/dashboard.md` in this directory, mounted into the container, and the self-signed certificate is written to `data/tls/` there. `make run PORT=9000` listens on that port. `make help` lists the targets.

## GitHub Container Registry

The Container workflow tests the app, builds the image, packages tags from `package.json`, and publishes to GHCR. Pull requests build and smoke-test the image and do not publish. `master` publishes `ghcr.io/rbe/dashboard:edge` and `ghcr.io/rbe/dashboard:sha-<commit>`. A tag `vX.Y.Z` that matches `package.json` also publishes `X.Y.Z`, `X.Y`, `X`, and `latest`.

```sh
podman pull ghcr.io/rbe/dashboard:latest
```

The published image is `linux/amd64`. `NODE_VERSION` in that workflow (and `make build NODE_VERSION=22`) selects the Node major inside the image.

## Package

```sh
npm test
npm run package:binary
```

`package:binary` writes a single executable for the current platform to `build/dashboard`. On macOS, `node scripts/build-binary.mjs --macos` writes `build/dashboard-macos` for Apple silicon. Tagging `vX.Y.Z` (matching `package.json`) builds that binary and the npm tarball and attaches both to the GitHub release. The same tag publishes the container image.
