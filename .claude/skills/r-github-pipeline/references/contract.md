# Divergences and the contract test

## Divergences

A project writes a divergence under "Divergences" in `docs/pipeline-rules.md`. A divergence is a match only when this list allows it.

Allowed, when the project differs in fact:

- `publish-github` for a JAR release or a binary release.
- No `docs` job when there is nothing to render.
- No `publish-container` for a library.
- In a Gradle project, `publish-container` may build the image from the tested JAR, and the workflow then passes no image tar.
- Extra laptop targets, such as `dev` and `verify`, that no job calls.

Not allowed: logic in the YAML, and a divergence from a rule under the top-level `<rules>` of `SKILL.md`.

## Contract test

The test of the repository reads the workflow, the Makefile, and `sdlc.mk`. Report mode records each condition in `templates/contract-report.md`. Setup mode repairs a missing workflow rule. The test fails when:

- there is not exactly one workflow, or the job ids and `needs` differ from the graph in `references/workflow.md`
- a `run:` step is not `make <target>`. This includes a step that runs `./gradlew`, `npm`, `podman login`, `python`, or `tar` in place of `make build`, `make login`, `make setup`, `make test`, `make docs`, or `make publish-container`
- an upload has no `retention-days`, or an intermediate artifact is kept more than 1 day, or `report` is kept more than 14 days
- `publish-*` is not limited to the default branch or the dispatch input, or it does not need `build` and `test`
- `report` is not the last job or has no `!cancelled()`
- the Makefile does not include `.claude/skills/r-github-pipeline/sdlc.mk` before any target, or a root `sdlc.mk` is the include
- `make test`, `make build`, or `make setup` runs no recipe, which means that the include switch lost a contract target

A repository that uses Make and does not publish through GitHub does not fail this test. That repository does not install this skill.
