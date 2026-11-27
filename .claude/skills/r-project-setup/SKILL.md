---
name: r-project-setup
description: Applies or checks the Make contract in setup mode or report mode. Use when adding a Makefile, CLAUDE.md, EditorConfig, or a standard target, or when moving a host tool into a target. A repository that does not publish through GitHub installs only this skill.
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill owns the Make contract: the Makefile, the standard targets, `CLAUDE.md`, and `.editorconfig`. Setup mode brings a project into line with the contract. Report mode shows the project against it.
</purpose>

<mode name="setup">
<steps>
1. Ask the owner how the project ships: as a binary, as a container image, as a library package, or with the merge only. A project that ships nothing answers with the merge only. Copy no template before the answer.
2. Write the Makefile.
   - If the project has no Makefile, ask which installed language skill the project uses. Write the Makefile from the template of that skill with the file tool: `templates/Makefile.python` in `r-python`, `templates/Makefile.node` in `r-node`, `templates/Makefile.gradle` in `r-jvm`, or `templates/Makefile.golang` in `r-go`. Write the other files that the comment at the top of the template names the same way. The template includes the language file of that skill after `project.mk`: `node.mk`, `python.mk`, `go.mk`, or `jvm.mk`. That file has the language targets, so the Makefile holds no copy of them.
   - For an existing Makefile, add only the lines of the template that it lacks.
   - The Makefile sets the variables, then includes `.claude/skills/r-project-setup/project.mk` before any target. If it includes `.claude/skills/r-github-pipeline/sdlc.mk`, leave this include out. That file provides `help` and the same targets.
3. Fill the command variables. Read `references/makefile.md` for the variables. Read `references/setup-cases.md`, "A command variable", before you set one, and when a recipe runs a tool on the host.
4. If the Makefile came from a template in this run, or a file that the tooling target writes is missing, run the tooling target that the language skill names.
5. Add each missing line to `.gitignore`: `build/`, `apm_modules/`, `docs/adr/index.toon`, `docs/skill-index.toon`, and the lines that the tooling reference of the language skill names.
6. Run `make toon`. Step 7 fills the brackets of the template from `docs/skill-index.toon`.
7. Write `CLAUDE.md`. If the file is missing, copy `templates/CLAUDE.md` and fill each bracket from the project and from `docs/skill-index.toon`. The answer of step 1 is the ship sentence. If the file exists, read `references/setup-cases.md`, "An existing `CLAUDE.md`".
8. Make each item of `<checks>` true, in order. Stop at the first item that cannot be made true.
   - Write a missing `.editorconfig` from `templates/editorconfig`.
   - Set `FORMAT_CMD`, `FORMAT_FIX_CMD`, `LINT_CMD`, and `INTEGRATION_CMD` as step 3 says. Leave an integration test out of `TEST_CMD`.
   - If a test has no id, read `references/setup-cases.md`, "A test with no id".
9. If each required command variable is set, or the Makefile defines that target, run `make setup`. Otherwise leave the run for later and name the empty variable.
10. Commit every file that this mode wrote, and each of these that exists: the manifest and its lockfile, `.claude/skills/`, `apm.yml`, and `apm.lock.yaml`. Push.
</steps>
<rules>
- Do not define a target of the Make contract again after the include. Those targets are `setup`, `build`, `test`, `editorconfig`, `format`, `format-fix`, `lint`, `integration`, `coverage`, `test-changed`, `help`, and `doctor`. To change what one does, set its command variable before the include.
- Do not add `sdlc.mk` or a workflow. Version tags, GHCR, and cleanup are `r-github-pipeline`.
- If a `project.mk` is at the repository root, leave its bytes and name it in the report.
</rules>
</mode>

<mode name="report">
<steps>
1. Read `templates/contract-report.md`, `project.mk`, and `references/fail-list.md` in this skill. Read the `Makefile` and `CLAUDE.md` of the project.
2. If there is no `Makefile`, mark every row that needs one as `missing`. Otherwise read which target `.DEFAULT_GOAL` names in the `Makefile` and in the makefile that it includes.
</steps>
<rules>
- Do not run `make setup`, `make build`, `make test`, `make docs`, or `make login`.
</rules>
</mode>

<checks>
1. `editorconfig` runs editorconfig-checker, and `.editorconfig` exists.
2. `format` and `format-fix` run the one formatter that the language skill names, and `format-fix` rewrites the files. Do not write a formatter or add a second one. The formatter does not format `.claude/`, `apm_modules/`, `build/`, or `docs/`.
3. `lint` runs the one linter that the language skill names.
4. `test` runs the unit tests and no integration test.
5. `integration` is the one integration entry. No second integration target exists.
6. `coverage` writes its report through diff-cover, and `COVERAGE_CMD` also writes the coverage map. The language skill names the coverage tool. The diff is the branch against `DEFAULT_BRANCH`. `coverage` and `test-changed` fail until the first unit test exists.
7. `test-changed` selects the tests from the coverage of the files in the diff, not from a hand-kept list.
8. Each test follows the test rules of `r-record`.
9. When `r-project-report` is installed, `make project-report` writes its file.
</checks>

<rules>
- Setup mode leaves a target that the project already filled in.
- `help` is the default goal. A project Makefile sets `.DEFAULT_GOAL` to no other target. A `##` comment on the target line is the text that `help` prints. `help` groups the targets as `help.mk` says. A target of the product Makefile is in the group `Project`.
- The standard targets, and when each exists, are in `references/makefile.md`.
- A target does the same thing on a laptop and in CI. A command that only makes sense on a laptop gets its own name, such as `dev` or `verify`.
- A target is filled in when its command variable has a non-empty value, or when the Makefile of the project gives that target a recipe. `true` is a filled-in value.
- A target that the project adds after the include is the project's.
- The project includes the installed `project.mk`. Do not keep a copy at the repository root or elsewhere.
- If the Makefile lacks the include of `project.mk` or `sdlc.mk`, run `make -f .claude/skills/<skill>/<file>.mk <target>`.
- Podman: `make build` and `make test` call Podman. `make run` exists only where a language template defines it. A recipe calls `git`, `podman`, and the tools of POSIX `sh`, such as `sed`, `awk`, `grep`, `find`, and `tar`. `setup` runs `make doctor`, then `SETUP_CMD`.
- Host mode: with `TOOLS=host`, each command variable runs its tool from `PATH` in place of Podman. `make host-tools` installs the pinned shared tools. A command variable of a project uses `$(PYTHON)`, `$(RUFF)`, `$(COVERAGE_PYTHON)`, `$(NODE)`, `$(GO)`, or `$(GRADLE_RUN)`, not a literal `podman run`, so host mode reaches it.
- Make 3.81 recipes: the system `make` stays GNU Make 3.81, also on macOS. Use no `.ONESHELL` and no Make 4 function (`$(file ...)`, `$(guile ...)`, `!=`). Each recipe line is one POSIX shell, joined with backslashes. A shell `$` is `$$`. The recipe is the command; add no shell-script wrapper.
</rules>

<references>
- `references/makefile.md`: the standard targets and when each exists, each variable and its default, a sample Makefile, and what each makefile of this skill provides. Read it before you set a variable, when a target fails, or when `make doctor` prints `FAIL`.
- `references/fail-list.md`: the conditions under which a repository fails this contract. Read it in report mode, and when `r-review` checks a change to the Makefile or to a workflow.
- `references/setup-cases.md`: the rules of setup mode for one case: a command variable, an existing `CLAUDE.md`, and a test with no id. Read the named section when step 3, 7, or 8 says so.
- `references/paths-and-shipment.md`: the rules for the paths of config, data, state, and cache, and for what a shipment may contain. Read it when the project reads or writes such a path, or ships a binary.
</references>
