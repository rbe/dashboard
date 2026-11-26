# When a repository fails the Make contract

Report mode records each condition in the skeleton `templates/contract-report.md`. Setup mode repairs a missing file, a missing include, or an empty command variable.

The repository fails this contract when:

- `make` with no goal runs anything other than `help`
- `CLAUDE.md` is missing, or it does not hold the stages, the installed language skills and subskills, and the import line `@.claude/skills/r-project-setup/rules.md`, or it holds a copy of that file
- `setup`, `build`, or `test` is missing, `docs` is missing while the repository renders docs, `login` is missing while an image is published, or one of those targets is not `.PHONY`
- `doctor`, `skills-install`, `skills-update`, or `old-board` is missing
- `SETUP_CMD`, `BUILD_CMD`, or `TEST_CMD` is empty, or `DOCS_CMD` is empty while the repository renders docs
- a person, an agent, or a workflow step runs Gradle, npm, Podman, python, or tar directly, except the one `podman run` line of the README, instead of `make setup`, `make build`, `make test`, `make docs`, or `make login`
- the Makefile does not include `.claude/skills/r-project-setup/project.mk` before any target, unless it includes `.claude/skills/r-github-pipeline/sdlc.mk` instead, or a root `project.mk` is still the include
- the Makefile defines a target of the Make contract again after the include, instead of setting its command variable. No template is an exception
- the Makefile uses `.ONESHELL` or a Make 4 function, or the standard targets call out to a shell script
- a recipe calls a host tool that the Podman rule in `SKILL.md` does not allow, or `setup` installs a tool on the host
- `.editorconfig` is missing, or `editorconfig` does not run editorconfig-checker
- `format` or `lint` is missing, a second formatter or a second linter is a target, or either target runs a linter or formatter written for this project
- `integration` is missing or is not the only integration entry
- `coverage` does not write `build/coverage/diff.md` for the lines that this change touched, or the result is a repository-wide percentage
- `test-changed` is missing, it selects tests from a hand-kept list, or CI runs `test-changed` in place of `test`
- a test has no `id:` in its header or metadata
- `r-project-report` is installed and `make project-report` does not write `build/project-report.md`, or that file is hand-edited
- CI runs a formatter, a linter, a test, or coverage by any command other than `make <target>`
