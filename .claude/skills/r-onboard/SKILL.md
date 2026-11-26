---
name: r-onboard
description: Brings a new or an existing project onto this skill collection in one run. Use when the owner says report and integrate, onboard, adopt, or add the skills to a project. Runs r-migrate-docs, r-project-setup, r-github-pipeline, r-record, and every gate, in order. Writes no feature.
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill is the order of the other skills. Each skill named in a step owns the work of that step.
</purpose>

<steps>
1. If `CLAUDE.md` is missing or has no `<general_rules>` block, read `.claude/skills/r-project-setup/templates/CLAUDE.md`. Its general rules apply to this run.
2. Run `make -f .claude/skills/r-project-setup/doctor.mk doctor`. If the target fails, stop and tell the owner each `FAIL` line and its fix.
3. Read the project before you ask a question.
   - Name the language from the manifest and the file types: `package.json`, `build.gradle`, `go.mod`, `pyproject.toml`, `*.py`, or a shell recipe.
   - Run `make -f .claude/skills/r-project-setup/old-board.mk old-board`. A failure of this target does not stop this run. Step 5 handles it.
   - Name `AGENTS.md` if it exists.
   - Read each of `Makefile`, `CLAUDE.md`, `README.md`, and `.github/workflows/` that exists.
   - Run `git remote get-url origin`. Take the host, the owner, and the name from the result. If there is no remote `origin`, name that in the reply. Ask the owner for the owner and the name only if step 8 runs.
   - Run `git branch --show-current` to read the default branch.
4. Ask the owner how the project ships, as setup step 1 of `r-project-setup` says. That step does not ask again in this run. A project on `github.com` that ships an image publishes through GitHub. If the project does not publish through GitHub, leave `r-github-pipeline` out of `apm.yml` and out of the skill list of `CLAUDE.md`.
5. If the old board or `AGENTS.md` exists, run `r-migrate-docs`.
6. Run `r-project-setup` in report mode. If the project publishes through GitHub, also run `r-github-pipeline` in report mode. Write both reports in the reply before any change to the Makefile, `CLAUDE.md`, or `.claude/skills/`.
7. Run `r-project-setup` in setup mode. If the language has no installed skill, no template exists. Stop, name the language, and ask the owner whether to write the Makefile by hand.
8. If the project publishes through GitHub, run `r-github-pipeline` in setup mode. Check that `make test` runs the tests after the include changed. Commit and push.
9. Ask `r-record` to write each rule that the project already follows. If the code already breaks a rule of an installed skill or of an ADR, that break gets a roadmap row of the kind `defect`. A requirement row with no test is allowed in this run, and `make project-report` lists it. Commit and push.
10. Run the six gates, then `make ids`, `make toon`, `make links-check`, and `make project-report`. If the project has a workflow, also run `make ci`. If a target fails, stop and fix the cause. Leave each check as strict as it was, and skip none. On the default branch the diff is empty, so `make coverage` reports no line and is only a smoke check.
11. Run `git ls-remote --tags` with the URL of the `git:` source of the collection in `apm.yml`. If the source is `owner/name`, the URL is `https://github.com/owner/name`. If the source is another form, skip this step. If the command lists a tag, read `references/skill-version.md`.
12. Write the reply in this order:
    - what the project is;
    - what changed in each commit;
    - which gate passed, and which gate did not run and why;
    - what only the owner can do. Candidates are a `GH_TOKEN` in the environment for the cleanup targets on a laptop, the package permission of the repository on GitHub, the first `vMAJOR.MINOR.PATCH` tag, and the first publish from the Actions tab;
    - that the first slice starts with `r-plan`.
</steps>

<rules>
- The owner's request to integrate covers the commits of this run and the push to the remote that the project already has. Push to no other remote.
- This run writes no feature, no fix, and no refactor.
- A file or the owner states the language, the shipment, and the owner of the repository. A guess does not.
- When the run ends, no file of the old board exists beside the new board.
</rules>
