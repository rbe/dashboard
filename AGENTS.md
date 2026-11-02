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

The workflow is `.github/workflows/ci.yml`. Its jobs are `setup`, `build`, `test`, `npm-package`, `docs`, `publish-npm`, `publish-container`, and `report`. Delivery is the container image. This repository does not publish a GitHub release. A push to `master` or `main` runs `publish-container` after the jobs it needs, and runs `publish-npm` when the repository variable `NPM_PUBLISH` is `true`. A `v*.*.*` tag uses the same rule. Any other branch runs through `report` and does not publish. `report` is the last job. It still runs when publish is skipped, and collects make output, script output, test results, coverage, and publish results into one artifact. `workflow_dispatch` starts one selected job. That includes `publish-container`, and that run publishes. `report` runs after it.

Do not weaken the workflow contract test to make a one-off pass.

Packages and images leave out `.claude/`, `AGENTS.md`, and `docs/`.

## Notes

- [Pipeline rules](docs/pipeline-rules.md)
- [Bugs](BUGS.md)
- [Waves](WAVES.md)
- [Features](FEATURES.md)
