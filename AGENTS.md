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

Do not weaken the workflow contract test to make a one-off pass.

Packages and images leave out `.claude/`, `AGENTS.md`, and `docs/`.

## Notes

- [Pipeline rules](docs/pipeline-rules.md)
- [Bugs](BUGS.md)
- [Waves](WAVES.md)
- [Features](FEATURES.md)
