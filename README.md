# Dashboard

Local markdown dashboard for systems and links. The board is stored in a file on this machine.

## Install

### macOS binary

GitHub Releases include `dashboard-macos`, one universal binary for Apple silicon and Intel. Node.js is not required.

```sh
chmod +x dashboard-macos
xattr -d com.apple.quarantine dashboard-macos
./dashboard-macos
```

Open http://127.0.0.1:4173. The binary is ad-hoc signed, so the first launch may need approval in System Settings → Privacy & Security.

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

The dev server listens on http://127.0.0.1:5173. `npm run preview` builds and serves the production UI on http://127.0.0.1:4173.

```sh
dashboard --help
dashboard --port 4173 --file data/dashboard.md
```

`PORT` and `DASHBOARD_FILE` set the same values. The default file is `data/dashboard.md` in the current directory.

## Package

```sh
npm test
npm run package:binary
```

`package:binary` writes a single executable for the current platform to `build/dashboard`. On macOS, `node scripts/build-binary.mjs --universal-macos` writes `build/dashboard-macos`. Tagging `vX.Y.Z` (matching `package.json`) builds that universal binary and the npm tarball and attaches both to the GitHub release.
