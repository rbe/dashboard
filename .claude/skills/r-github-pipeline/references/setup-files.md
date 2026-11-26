# Files of setup mode and report mode

A path that starts with `templates/`, and `sdlc.mk` and `container.mk`, are files of this skill. Every other path is a file of the project.

## Files to read

| File | Use |
| --- | --- |
| `sdlc.mk` | The makefile that the project includes |
| `container.mk` | The image targets of a project that has no recipe of its own for them. `sdlc.mk` includes it |
| `templates/Makefile.node`, `templates/ci.node.yml` | Node toolchain. A Node app, image only. Node 24 is the toolchain of this template only |
| `templates/Makefile.gradle`, `templates/ci.gradle.yml` | Gradle toolchain. A Gradle app, image plus a JAR release. The JDK image in the template is its toolchain |
| `templates/ci.make.yml`, `templates/Makefile.image` | The workflow and the image block of a project on the Makefile of its language skill: Python, Go, or another language |
| `templates/Containerfile.node`, `templates/Containerfile.gradle`, `templates/Containerfile.python`, `templates/Containerfile.golang` | The source of `Containerfile`, by toolchain |
| `templates/publish-client.yml` | The source of `.github/workflows/publish-client.yml`, for a project with `client/package.json` |
| `templates/pipeline-rules.md` | The source of `docs/pipeline-rules.md` |
| `templates/containerignore`, `templates/gitignore` | The source of `.containerignore` and `.gitignore` |
| `templates/contract-report.md` | The skeleton of report mode |
| `Makefile`, `.github/workflows/`, `docs/pipeline-rules.md`, `Containerfile`, `.containerignore`, `.gitignore` | The project, when present |

The Node template and the Gradle template are for a project that has no language Makefile of its own. They have the placeholder lines `NAME ?= app` and `OWNER ?= owner`. Replace both values with the name and the owner of the repository. A project diverges from a template only when it has a different output or toolchain, and it writes that down as a divergence.

## The include switch

If the Makefile includes `project.mk` or `.claude/skills/r-project-setup/project.mk`, do these steps:

1. Change the include to `.claude/skills/r-github-pipeline/sdlc.mk`.
2. Remove the `project.mk` include.

`sdlc.mk` provides `help`, and it includes `contract.mk`, the contract targets of `r-project-setup`: `setup`, `build`, `test`, `format`, `lint`, `coverage`, and the others. The command variables of the language Makefile therefore keep their effect.

A project never defines a contract target again. The Node template and the Gradle template set the command variables of `r-project-setup` (`SETUP_CMD`, `BUILD_CMD`, `TEST_CMD`, `FORMAT_CMD`, `FORMAT_FIX_CMD`, `LINT_CMD`, `INTEGRATION_CMD`, `COVERAGE_CMD`, `TEST_CHANGED_CMD`, `DOCS_CMD`) before the include, like the language templates do. They add the variables of the pipeline: the image variables of `container.mk`, `RENDER_DOCS`, and `PUBLISH_IMAGE`. They do not include the language template, because that one includes `project.mk` and `sdlc.mk` already defines `help`. They include the language file after `sdlc.mk`: `node.mk` of `r-node` in the Node template, and `jvm.mk` of `r-jvm` in the Gradle template. So the targets `npm`, `node-tooling`, `wrapper`, `jvm-tooling`, and `podman-socket` exist there. The commands differ from the language templates, because these templates run `npm test` and `npm run integration`, pack the dependencies for the next job, and build the image.
## The image block of a language Makefile

A project on the Makefile of the `r-python` skill, the `r-go` skill, or the `r-node` skill does these steps. A Gradle project that ships an image uses `templates/Makefile.gradle` instead. That template includes `jvm.mk` of the `r-jvm` skill, so the targets `jvm-tooling` and `wrapper` exist there. Run the target `jvm-tooling` once first.

1. Take the image block of `templates/Makefile.image`.
2. Leave `OWNER` and `NAME` unset. They default to the owner and the repository name in `git remote get-url origin`. Set them only if the project has no remote or has another name.
3. Copy the `Containerfile` template of the language. Change `PACKAGE` or `NAME` in it.
4. Use `templates/ci.make.yml` as `.github/workflows/ci.yml`.
5. `templates/Containerfile.golang` needs `cmd/<name>/` and copies `cmd/` and `internal/`. Change its `COPY` lines for another layout. `templates/Containerfile.node` runs `npm run build` and starts `dist/server.js`. A Node project with no build script changes both. The `BUILD_CMD` of the `r-node` skill runs `npm pack`. An app that is no library replaces it with `true` before the image line.

`make build` then builds the image, runs the smoke check, and saves the image tar.

## What the image and the repository contain

- The image copies named files, not the work tree.
- `templates/containerignore` is the list of paths that `.containerignore` keeps out of the image build. The list is `.git`, `.github`, `.claude/`, `apm_modules/`, `CLAUDE.md`, `docs/`, `build/`, `node_modules`, `data/`, `.env`, `.env.*`, and `*.tar`.
- `.claude/skills/` is committed, because Make includes files from it. The image still excludes `.claude/`.
- `templates/gitignore` is the list of paths that `.gitignore` keeps out of Git: build output, image tars, `data/`, and `.env`.
