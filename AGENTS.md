# Agent notes

The Makefile is the interface. A laptop and CI run the same targets. Workflow YAML calls `make`. Podman is the only container engine. Node 24 stays in the image, so the host does not need Node.

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
| Image | `ghcr.io/rbe/dashboard` |

`NAME` in the Makefile is the npm package name and the GitHub repository name. Do not commit `data/`.

The workflow is `.github/workflows/ci.yml`. Its jobs are `setup`, `build`, `test`, `docs`, `publish-container`, and `report`. Delivery is the container image. `build`, `test`, and `docs` need `setup` and run together. `docs` needs only `setup`. `publish-container` needs `build` and `test`. It runs on a push to `master` or `main`, and when `workflow_dispatch` selects it. Any other branch skips it. `report` is last, after `publish-container`. It still runs when that job is skipped or fails, and collects make output, script output, test results, coverage, and publish results into one artifact. `workflow_dispatch` starts one selected job. A manual `publish-container` may push. A publish tags `<version>-<run>` and `latest`. `<version>` is the nearest v* tag on the commit with the leading `v` removed, and `<run>` is the GitHub run number. The job does not push `edge` or a bare `sha-<commit>` tag. If that tag is missing, the publish fails and does not invent a version. After a successful push, `prune-package-versions` keeps the current published version and exactly one former. One published version means it deletes nothing. `latest` is a tag on the newest version, not another package version. A skipped or failed publish deletes nothing.

Do not weaken the workflow contract test to make a one-off pass.

Packages and images leave out `.claude/`, `AGENTS.md`, and `docs/`.

## Notes

- [Waves](docs/WAVES.md)
- [Features](docs/FEATURES.md)
- [Bugs](docs/BUGS.md)
- [Pipeline rules](docs/pipeline-rules.md)
