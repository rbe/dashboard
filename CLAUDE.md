# dashboard

Local markdown dashboard for systems and links. The board is stored in a file on this machine.

`CLAUDE.md` is the only entry file. The skills are under `.claude/skills/`.

Stages, in order: `r-plan`, `r-develop`, `r-review`, `r-release`. A new or vague request starts at `r-plan`. A request that names a source file, a failing test, or a roadmap defect starts at `r-develop`. Other skills: `r-record`, `r-project-report`, `r-project-setup`, `r-migrate-docs`, `r-github-pipeline`, `r-skills-review`, `r-component-upgrade`, `r-onboard`, `r-system-state-report` (say `state report`), `r-board-merge-report`, `r-board-merge`. Language skills: `r-node`, `r-shell`. Subskills `r-plan` asks and `r-review` checks: `r-security`, `r-ux-ui-design`, `r-api-design`, `r-observability`, `r-performance`, `r-privacy`. A project skill is an extra name listed here. If `CLAUDE.md` lists a project skill `<project>-<stage>`, the stage reads it after its own steps. The addendum holds only what is true for that project. There is no project skill.

This project ships as a container image, with a manual publish. The skills are installed with APM from `apm.yml`, and `apm.lock.yaml` pins the commit of `rbe/ralfskills`.

## Product

|                     |                                                  |
| ------------------- | ------------------------------------------------ |
| Name                | dashboard                                        |
| Vite dev server     | http://127.0.0.1:5173 (`npm start`)              |
| Podman HTTPS server | https://127.0.0.1:4173 (`make run`)              |
| Data file           | `data/dashboard.md`                              |
| Data env            | `DASHBOARD_FILE`                                 |
| API                 | `/api/dashboard`, contract `shared/openapi.json` |
| Smoke needle        | `not for git`                                    |
| Image               | `ghcr.io/rbe/dashboard`                          |
| Default branch      | `master`                                         |

`NAME` in the Makefile is the npm package name and the GitHub repository name. Do not commit `data/`.

The pipeline rules and their divergences are in `docs/pipeline-rules.md`. The workflow is `.github/workflows/ci.yml`. The Makefile includes `.claude/skills/r-github-pipeline/sdlc.mk` before any target.

`@rbe/dashboard-client` is a separate package in `client/`. Its contract is `shared/openapi.json`. `.github/workflows/publish-client.yml` packs that package, creates a GitHub Release, and publishes it to GitHub Packages on `workflow_dispatch` and tags `client-v*`. It does not call `make` and it does not publish the container image.

Packages and images leave out `.claude/`, `.cursor/`, `CLAUDE.md`, and `docs/`.

The general rules, the Agents section, and the communication contract stand once, in `rules.md` of `r-project-setup`. The next line imports that file. Do not copy it here.

@.claude/skills/r-project-setup/rules.md
