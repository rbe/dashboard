# Files of setup mode and report mode

A path that starts with `templates/`, and `sdlc.mk` and `container.mk`, are files of this skill. Every other path is a file of the project.

## Files to read

| File | Use |
| --- | --- |
| `sdlc.mk` | The makefile that the project includes |
| `container.mk` | The image targets of a project that has no recipe of its own for them. `sdlc.mk` includes it |
| `templates/ci.yml` | The source of `.github/workflows/ci.yml` for every language. Marked optional blocks: Node, Image, JAR, Release. Delete the blocks that the project does not need |
| `templates/Makefile.image` | The image block of a project on the Makefile of its language skill: Python, Go, Node, Gradle, or another language. Marked optional blocks: Node web app, JAR, Release (`publish-github`) |
| `templates/Containerfile.node`, `templates/Containerfile.gradle`, `templates/Containerfile.python`, `templates/Containerfile.golang` | The source of `Containerfile`, by toolchain |
| `templates/publish-client.yml` | The source of `.github/workflows/publish-client.yml`, for a project with `client/package.json` |
| `templates/pipeline-rules.md` | The source of `docs/pipeline-rules.md` |
| `templates/containerignore`, `templates/gitignore` | The source of `.containerignore` and `.gitignore` |
| `templates/contract-report.md` | The skeleton of report mode |
| `Makefile`, `.github/workflows/`, `docs/pipeline-rules.md`, `Containerfile`, `.containerignore`, `.gitignore` | The project, when present |

The language template of the language skill and `templates/Makefile.image` together make the Makefile of a project that has no Makefile yet. The placeholder lines `NAME ?= app` and `OWNER ?= owner` of the language template stay until the owner and the name of the repository replace them. A project diverges from a template only when it has a different output or toolchain, and it writes that down as a divergence.

## The include switch

If the Makefile includes `project.mk` or `.claude/skills/r-project-setup/project.mk`, do these steps:

1. Change the include to `.claude/skills/r-github-pipeline/sdlc.mk`.
2. Remove the `project.mk` include.

`sdlc.mk` provides `help`, and it includes `contract.mk`, the contract targets of `r-project-setup`: `setup`, `build`, `test`, `format`, `lint`, `coverage`, and the others. The command variables of the language Makefile therefore keep their effect.

A project never defines a contract target again. The language template sets the command variables of `r-project-setup` (`SETUP_CMD`, `BUILD_CMD`, `TEST_CMD`, `FORMAT_CMD`, `FORMAT_FIX_CMD`, `LINT_CMD`, `INTEGRATION_CMD`, `COVERAGE_CMD`, `TEST_CHANGED_CMD`) before the include. `templates/Makefile.image` adds the variables of the pipeline: the image variables of `container.mk`, `PUBLISH_IMAGE`, and, in its Release block, `publish-github`. Set `RENDER_DOCS = 1` to render `docs/` with the shared renderer. The Makefile includes `sdlc.mk` instead of `project.mk`, and then the language file: `node.mk` of `r-node`, `jvm.mk` of `r-jvm`, and so on. So the language targets exist there.
## The image block of a language Makefile

A project on the Makefile of the `r-python` skill, the `r-go` skill, the `r-node` skill, or the `r-jvm` skill does these steps. A Node web app keeps the Node block of `templates/Makefile.image`. A Gradle project that builds the image from the tested JAR keeps the JAR block, and the Release block when it publishes a GitHub release.

1. Take the image block of `templates/Makefile.image`.
2. Leave `OWNER` and `NAME` unset. They default to the owner and the repository name in `git remote get-url origin`. Set them only if the project has no remote or has another name.
3. Copy the `Containerfile` template of the language. Change `PACKAGE` or `NAME` in it.
4. Use `templates/ci.yml` as `.github/workflows/ci.yml`. Delete the optional blocks that the project does not need, with both comment lines of each block.
5. `templates/Containerfile.golang` needs `cmd/<name>/` and copies `cmd/` and `internal/`. Change its `COPY` lines for another layout. `templates/Containerfile.node` runs `npm run build` and starts `dist/server.js`. A Node project with no build script changes both. The `BUILD_CMD` of the `r-node` skill runs `npm pack`. An app that is no library replaces it with `true` before the image line.

`make build` then builds the image, runs the smoke check, and saves the image tar.

## What the image and the repository contain

- The image copies named files, not the work tree.
- `templates/containerignore` is the list of paths that `.containerignore` keeps out of the image build. The list is `.git`, `.github`, `.claude/`, `apm_modules/`, `CLAUDE.md`, `docs/`, `build/`, `node_modules`, `data/`, `.env`, `.env.*`, and `*.tar`. Example data ships only from `examples/`, when the path and the name say that it is an example.
- `.claude/skills/` is committed, because Make includes files from it. The image still excludes `.claude/`.
- `templates/gitignore` is the list of paths that `.gitignore` keeps out of Git: build output, image tars, `data/`, and `.env`.
