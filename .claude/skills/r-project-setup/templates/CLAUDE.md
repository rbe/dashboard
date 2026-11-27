# [project name]

[One sentence that says what this project is.]

`CLAUDE.md` is the only entry file. The skills are under `.claude/skills/`.

Stages, in order: `r-plan`, `r-develop`, `r-review`, `r-release`. A new or vague request starts at `r-plan`. A request that names a source file, a failing test, or a roadmap defect starts at `r-develop`. Other skills: `r-record`, `r-project-report`, `r-project-setup`[, `r-onboard`, `r-migrate-docs`, `r-github-pipeline`, `r-system-state-report` (say `state report`), `r-board-merge-report`, `r-board-merge`, `r-skills-review`, `r-component-upgrade`: keep each installed one]. Language skills: [the installed ones of `r-node`, `r-python`, `r-shell`, `r-jvm`, `r-go`]. Subskills `r-plan` asks and `r-review` checks: [the installed ones of `r-security`, `r-privacy`, `r-ux-ui-design`, `r-api-design`, `r-observability`, `r-performance`]. A project skill is an extra name listed here. If `CLAUDE.md` lists a project skill `<project>-<stage>`, the stage reads it after its own steps. The addendum holds only what is true for that project. [Name each project skill, or none.]

This project ships [as a binary, with `make <target>` / as a container image, with a manual publish / as a library package, with `make build` / with the merge only].

The general rules, the Agents section, and the communication contract stand once, in `rules.md` of `r-project-setup`. The next line imports that file. Do not copy it here.

@.claude/skills/r-project-setup/rules.md
