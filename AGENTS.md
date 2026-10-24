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
| macOS binary | `build/dashboard-macos` |

`NAME` in the Makefile is the npm package name and the GitHub repository name. Do not commit `data/`.

## Commands

- `npm start` is the Vite dev server.
- `make run` and `make stop` are the Podman HTTPS server. `make build` builds that image.
- `make host-checks` is the Linux CI check: `npm ci`, `npm test`, the Linux binary, and the packed CLI smoke. It runs inside `podman run node:24-bookworm-slim`.
- `make ci` is a branch push: `make host-checks`, then `make ci-image`.
- `make resolve-ghcr-tags` resolves the GHCR tags from the git ref.
- `make npm-tarball` packs the npm tarball into `build/`.
- `make macos-binary` builds the Apple silicon binary. It runs on macOS only and uses Node 24 already on PATH.
- `make npm-publish` publishes to npm and refuses unless `NPM_PUBLISH=true`.
- `make help` lists every target. A description that starts with "Match CI" is a step the GitHub workflows run.

## Node and containers

Node 24. Host checks run inside the Node 24 image, so the host does not need Node. `make macos-binary` and `make npm-publish` are the exceptions: codesign and npm provenance need the host. Do not add Docker or a second image build.

## Workflows

YAML calls `make`. It does not call `npm ci`, `npm test`, or `npm pack`.

`host-test.yml` is called only from CI and Release. `container-image.yml` is called only from Container. One event runs the host checks once.

CI listens for every branch push and `workflow_dispatch`, not `pull_request`. Release listens for `v*.*.*` tags. Container listens for every branch push, those tags, and `workflow_dispatch`. A same-repo pull request is not tested twice. Fork pull requests do not run CI.

Image push happens only when `scripts/container-tags.mjs` sets `publish=true`. npm publish stays off unless the repository variable `NPM_PUBLISH` is `true`. GHCR login and `gh release` stay in the workflow files.

`scripts/workflows.test.mjs` locks this contract. Do not weaken those assertions to make a one-off change pass.
