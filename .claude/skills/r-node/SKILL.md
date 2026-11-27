---
name: r-node
description: Node and TypeScript. Applies the Node rules to a change. Use when r-node is installed and the files in hand are JavaScript or TypeScript. A framework named in CLAUDE.md is a reference file beside this skill. The stage skill still applies.
kind: language
files: [js, jsx, ts, tsx, mjs, cjs]
stages: [r-develop]
---

The general rules in `CLAUDE.md` apply.

<purpose>
This skill names the tools and the Make targets for JavaScript and TypeScript files.
</purpose>

<steps>
1. If the project has no `package.json`, or no Prettier and no ESLint, read `references/tooling.md` and run `make node-tooling`.
2. If `CLAUDE.md` names a framework, read `references/frameworks.md` and the file in `references/` that has the name of the framework.
3. Write source in `src/`. Use TypeScript if the project already uses it. A new file follows that choice.
4. To add a dependency, run `make npm ARGS='...'`. `make setup` installs the dependencies.
</steps>

<rules>
- The formatter is Prettier. The linter is ESLint, also for TypeScript.
- The comment at the top of `templates/Makefile.node` explains each command.
- The targets `npm` and `node-tooling` are in `node.mk` beside this skill. The Makefile includes it after `project.mk`.
- A library sets `exports` and `files` in `package.json`. `make build` then packs only the source. `references/tooling.md` has the command.
- A framework file does not replace this skill or the stage skill.
</rules>

<references>
- `references/tooling.md`: read it before you run `make node-tooling`, when you change `templates/Makefile.node` or `node.mk`, or when the project is a library.
- `references/coverage.md`: read it when the test runner is not `node --test`, or when `make coverage` or `make test-changed` fails.
- `references/frameworks.md` and a file named by a framework: read them when `CLAUDE.md` names that framework.
- `references/upgrade.md`: read it when `r-component-upgrade` updates a component of this language.
</references>
