# Make contract report

Skeleton for report mode. Fill a copy in the reply. Leave this file blank.

`State` is `matches` or `missing`. `Evidence` is a path, a variable, a hash, or a command. The verdict lists every row under one of those two words. A target is filled in when its command variable has a non-empty value, or the Makefile gives that target a recipe. This report writes nothing in the project.

Project:

Skill: r-project-setup

## Verdict

Matches:

-

Missing:

-

## Checks

The include is `.claude/skills/r-project-setup/project.mk`. A repository that includes `.claude/skills/r-github-pipeline/sdlc.mk` and leaves `project.mk` out matches that row: `sdlc.mk` already provides `help`.

| Check | State | Evidence |
| --- | --- | --- |
| `make` with no goal runs `help` | | |
| `CLAUDE.md` names the stages, the installed language skills and subskills, the `<general_rules>` block of the template, and the communication contract | | |
| The Makefile includes `.claude/skills/r-project-setup/project.mk`, or `sdlc.mk` from `r-github-pipeline` when that file provides `help` | | |
| The include sits before any target | | |
| `setup`, `build`, and `test` exist and are `.PHONY` | | |
| `editorconfig` runs editorconfig-checker | | |
| `format` is one existing formatter and `lint` is one existing linter | | |
| `integration` is the one integration entry | | |
| `coverage` writes `build/coverage/diff.md` for the lines this change touched | | |
| `test-changed` selects tests from coverage of the diff and CI still runs `test` | | |
| a test names its requirement with `id:` in the header or metadata | | |
| `r-project-report`, when installed, writes `build/project-report.md` and that file is not hand-edited | | |
| `docs` exists when the repository renders docs, and is absent otherwise | | |
| `login` exists when an image is published, and is absent otherwise | | |
| `SETUP_CMD`, `BUILD_CMD`, and `TEST_CMD` are non-empty | | |
| `DOCS_CMD` is non-empty when the repository renders docs | | |
| Gradle, npm, Podman, python, and tar run inside those targets | | |
| No `.ONESHELL`, no Make 4 function, no shell-script wrapper. GNU Make 3.81 | | |
| `setup` runs `make doctor` first and installs no tool on the host | | |
| `doctor`, `skills-install`, `skills-update`, and `old-board` exist | | |
| No recipe calls a host tool other than `git` and `podman` | | |

## Filled in

Setup mode leaves these recipes and these values.

| Target | Filled in | Where |
| --- | --- | --- |
| `setup` | | |
| `build` | | |
| `test` | | |
| `editorconfig` | | |
| `format` | | |
| `lint` | | |
| `integration` | | |
| `coverage` | | |
| `docs` | | |
| `login` | | |
