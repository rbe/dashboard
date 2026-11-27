<purpose>
This file gives the Node facts that `r-component-upgrade` needs. It adds no step.
</purpose>

<rules>
- The Node major version is `NODE_VERSION` in the Makefile. `NODE_IMAGE` and the `make image` build argument read it.
- The base image of the app is the `ARG NODE_VERSION` default in the Containerfile. It holds the same number as the Makefile.
- A package is in `package.json`. `package-lock.json` holds the resolved versions.
- The dev tools are the `NODE_DEV_TOOLS` of the Makefile. `make node-tooling` installs each one as an exact version.
- The smoke image of the pipeline is `CURL_IMAGE` in the Makefile.
- To change a package or the lock file, run `make npm ARGS='...'`.
- `make setup` runs `npm ci`. It never changes `package-lock.json`.
- A change of the Node major version changes all of these files in one slice. Each holds the same major.
  1. `.nvmrc`.
  2. `engines.node` in `package.json`.
  3. `NODE_VERSION` in the Makefile.
  4. The `ARG NODE_VERSION` default in the Containerfile.
  5. The Node version in the CI workflow, if it names one.
  6. The target of the bundler, if the project has one.
  7. `@types/node`.
- A fresh checkout has no `node_modules`. `make format` and `make lint` then run `npm ci` first.
</rules>

## Order of a major upgrade

A major upgrade of a Node project follows this order. Finish one group with the gates green before the next group. Skip a group that does not change. If a release note needs a newer version of an earlier group, upgrade that group first.

1. Node.
2. TypeScript.
3. ESLint and its plugins, as one step. Keep the versions compatible with each other.
4. Vite and its React plugin, and `esbuild` if `package.json` lists it.
5. React, `react-dom`, and their types.
6. Server libraries.
7. Other runtime libraries, one major version in each slice.

## Risks to check in each group

- Node: removed or deprecated APIs, a new OpenSSL or HTTP client behaviour, and native modules against `engines`.
- TypeScript: stricter checks, changes of the DOM types, and the interaction of `module` and `moduleResolution` with the bundler.
- ESLint: the flat config, renamed rules, and the major version that the TypeScript plugin pairs with.
- Vite: renamed options, the plugin API, and a default `target` that differs from the `esbuild` target.
- React: new defaults for concurrent rendering, changes of the types, and deprecated lifecycle methods.
- Server library: changed middleware signatures, removed helpers, and changed types.
