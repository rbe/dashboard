---
name: r-github-pipeline
description: Applies or checks the GitHub delivery contract in setup mode or report mode. One workflow calls Make targets. Use when adding CI, aligning a pipeline, or changing publish, versioning, the image, cleanup, or retention. Depends on r-project-setup.
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill owns the GitHub delivery contract and `sdlc.mk`, the makefile that implements it: version, publish tags, cleanup, and the pipeline report.
</purpose>

<mode name="setup">
<steps>
1. If the repository does not publish through GitHub, stop. That repository installs `r-project-setup` only, and this mode adds no workflow there.
2. Read `references/setup-files.md`. Read each project file that it lists.
3. Write `Makefile` when the include `.claude/skills/r-github-pipeline/sdlc.mk` is missing or stands after a target, or when a required target has no recipe and no command variable. If the Makefile includes `project.mk`, switch the include as `references/setup-files.md` says. Read `references/makefile.md` before you write a variable, a target, or a recipe.
4. Write `.github/workflows/ci.yml`. If there is no workflow, start from the template of the toolchain. If `ci.yml` exists, fix only a trigger, a permission, a missing `retention-days`, or a `run:` step that is not `make <target>`. Read `references/workflow.md` for the rules.
5. If `docs/pipeline-rules.md` is missing, copy `templates/pipeline-rules.md` and fill "This repository". If the file exists, leave "This repository" and "Divergences" as written.
6. If `Containerfile`, `.containerignore`, or `.gitignore` is missing, copy the template of the toolchain. In `Containerfile`, change the paths and the start command to those of the project. If `.containerignore` or `.gitignore` exists, add only the template lines that are missing.
7. Run `make setup`, `make build`, and `make test`. If one of them runs no recipe or prints that there is nothing to do, the include switch lost a contract target. Repair the Makefile.
8. Write each divergence under "Divergences" in `docs/pipeline-rules.md`. Read `references/contract.md` for the divergences that the contract allows.
</steps>
<rules>
- Add no tag trigger.
- Add no workflow beside `ci.yml` and delete no workflow. Name a second workflow file in the report.
- Leave the bytes of a root `sdlc.mk` and name it in the report. A root `sdlc.mk` is off the contract.
</rules>
</mode>

<mode name="report">
<steps>
1. Read `templates/contract-report.md`, all four reference files, and the project files that `references/setup-files.md` lists.
2. If the repository has no workflow and does not publish through GitHub, answer `yes` under `Applies` in the skeleton and leave the checks blank. The verdict is that this skill stays uninstalled.
3. Read which target `.DEFAULT_GOAL` names in the `Makefile` and in the makefile that it includes. Run `git describe --tags --abbrev=0 --match 'v[0-9]*'` to read the tag that `make version` accepts.
</steps>
<rules>
- Do not run `make publish-container`, `make publish-github`, or a cleanup target.
- This report is the contract report. `make report` writes a different report, `build/report/index.md`, for one pipeline run.
</rules>
</mode>

<rules>
- Each job id of the workflow is a Make target. `setup`, `build`, `test`, and `docs` come from the `r-project-setup` contract. `publish-container`, `publish-github`, and `report` come from this skill. `login` is a target that the publish job runs, not a job.
- The project Makefile includes the installed `sdlc.mk` before any target. Do not copy `sdlc.mk` to the repository root, and do not edit a file of this skill.
- The workflow is one file, `.github/workflows/ci.yml`, named `CI`. A step is `actions/checkout`, an artifact upload or download, or `run: make <target>`.
- `publish-*` runs only on a push to the default branch or when `workflow_dispatch` selects that job. It needs `build` and `test`. A tag push publishes nothing.
- A published version comes only from `make version`. A cleanup does not call it. A cleanup needs no git tag, and it keeps `PUBLISHED_TAG`, else the version in `build/publish-version.txt`, else the newest rolling version that GitHub lists.
- Every upload sets `retention-days`.
- The contract allows no second name for one target and no Docker in place of Podman.
- This skill ships no shell script.
- If a cleanup must be tried, set `DRY_RUN=1`. The cleanup then prints what it would delete and deletes nothing. A cleanup runs at any time, with or without `DRY_RUN=1`. Without `DRY_RUN=1` it deletes, also on a laptop. In CI, a ref that is not the default branch deletes nothing.
- If the contract test of the repository fails, repair the pipeline or record a divergence.
</rules>

<references>
- `references/setup-files.md`: the files each mode reads and writes, the include switch, the image block, and what the image contains. Read it in both modes.
- `references/workflow.md`: the job graph, triggers, permissions, artifacts, versioning, and retention. Read it in report mode, and in setup mode before you write `ci.yml` or change the version, publish, cleanup, or retention.
- `references/makefile.md`: the variables, the targets of `sdlc.mk` and `container.mk`, and the recipe helpers. Read it in report mode, and in setup mode before you write a variable, a target, or a recipe.
- `references/contract.md`: the allowed divergences and the conditions that fail the contract test. Read it in report mode, and in setup mode before you write a divergence or when the contract test fails.
</references>
