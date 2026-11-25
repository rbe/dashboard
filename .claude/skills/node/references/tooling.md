# Node tooling

## The Makefile template

- The variable `$(NODE)` runs Node and npm in Podman.
- `templates/Makefile.node` fills in each command variable for `node --test`, Prettier, and ESLint.
- `templates/prettierignore` and `templates/eslint.config.mjs` are the files that Prettier and ESLint need.

## `make node-tooling`

`make node-tooling` sets up a new project, or a project with no Prettier and no ESLint, in one run. It does these things:

1. It creates `package.json` with the name, the version `0.1.0`, and `type=module`. The name is the variable `NAME`. The default is the repository name of the remote `origin`, else the directory name.
2. It adds the dev tools in the variable `NODE_DEV_TOOLS` as exact versions.
3. It writes `.prettierignore`, `eslint.config.mjs`, and `.editorconfig`.
4. It adds `node_modules/` and `coverage/` to `.gitignore`.
5. It runs `make format-fix`.

A file or a dependency that is already in the project stays as it is, so the target is safe to run again.

Example: `make node-tooling NAME=my-app`

## A library

A library names what it ships: `make npm ARGS='pkg set exports=./src/index.js files[0]=src'`
