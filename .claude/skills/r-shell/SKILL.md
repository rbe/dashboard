---
name: r-shell
description: Sets the rules for POSIX shell inside a Make recipe. Use when r-shell is installed and the change is a recipe or a shell command. Make 3.81 rules are r-project-setup. The stage skill still applies.
kind: language
files: [sh]
names: [Makefile]
stages: [r-develop]
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill gives the rules for a Make recipe and for a shell command.
</purpose>

<rules>
- Write POSIX `sh`. If the change needs a bash feature, first ask `r-record` to write a requirement row that names bash, and name bash in `CLAUDE.md`.
- The formatter is shfmt. The linter is shellcheck. Both read `.sh` files. No template runs them. A project with `.sh` files sets `FORMAT_CMD` and `LINT_CMD` to run them in a Podman image.
- If the only shell of the project is in Make recipes, add no shell formatter and no shell linter.
- Apply the recipe rules of `r-project-setup`.
- If a recipe can fail, start it with `set -eu`.
</rules>
