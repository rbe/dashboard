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
- A change of the Node major version changes `NODE_VERSION` in the Makefile and the Containerfile default in the same slice.
- A fresh checkout has no `node_modules`. `make format` and `make lint` then run `npm ci` first.
</rules>
