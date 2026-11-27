---
name: r-component-upgrade
description: "Updates one component to a newer version: a library, a runtime, a base image, a tool pin, or this skill collection. Use when the owner asks to update, upgrade, or bump a version, or when a pin is outdated."
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill updates one component to a newer version in one slice. A component is a library, a language runtime, a base image, a tool pin of a makefile, or this skill collection. A tool pin is a variable that ends in `_VERSION` or `_IMAGE`.
</purpose>

<steps>
1. Name the one component, its current version, and the target version. Find the pin with a search of the makefiles and the manifests.
2. If the component is this skill collection, follow the Update section of the README and stop here.
3. Read the release notes between the two versions. List each breaking change that the project uses.
4. If the installed language skill of the component has the file `upgrade.md` in its `references` folder, read that file for the files, the commands, and the known traps of that environment.
5. Run the gates before the change. Keep the result as the baseline.
6. Change the one pin. If a lock file changes, use the Make target that `upgrade.md` names.
7. Run the gates again. Compare the result with the baseline.
8. Ask `r-record` for the history file. Give it the old version, the new version, the breaking changes, and the gate results before and after.
</steps>

<rules>
- One slice updates one component.
- If the update is a major version step, `r-plan` runs first, because the step can change a rule.
- A pin names an exact version. A pin never names `latest`.
- If a gate fails after the change and the cause is the new version, revert the pin. Then ask `r-record` for a roadmap row of the kind `defect`.
</rules>

<output>
- The component.
- The old and the new version.
- The breaking changes that the project uses.
- The gate results before and after the change.
</output>
