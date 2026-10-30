# Multi-stage image for the local markdown dashboard.
# The build stage installs dependencies and compiles the UI.
# The runtime stage serves that build with the project Node server.
# NODE_VERSION is the Node major. The CI workflow passes the same value.

ARG NODE_VERSION=24

FROM node:${NODE_VERSION}-bookworm-slim AS build

WORKDIR /src

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html tsconfig.json vite.config.ts ./
COPY src ./src
COPY scripts ./scripts
COPY data/dashboard.example.md ./data/dashboard.example.md

RUN npm run build

FROM node:${NODE_VERSION}-bookworm-slim AS runtime

WORKDIR /app

COPY --from=build /src/dist ./dist
COPY bin/dashboard.mjs ./bin/dashboard.mjs
COPY scripts/cli.mjs scripts/server.mjs scripts/dashboard-api.mjs scripts/tls-cert.mjs ./scripts/
COPY data/dashboard.example.md ./data/dashboard.example.md

# Root inside the container is the invoking user under rootless Podman,
# so the mounted board file stays owned by that user.
USER root

ENV PORT=4173
EXPOSE 4173

# The server defaults to 127.0.0.1, which published ports cannot reach.
ENTRYPOINT ["node", "bin/dashboard.mjs"]
CMD ["--host", "0.0.0.0"]
