const tgz = process.env.TGZ_NAME
const repo = process.env.GITHUB_REPOSITORY
const tag = process.env.GITHUB_REF_NAME
const version = tag && tag.startsWith('v') ? tag.slice(1) : tag
const image = repo ? `ghcr.io/${repo.toLowerCase()}:${version}` : ''
if (!tgz || !repo || !tag) {
  console.error('TGZ_NAME, GITHUB_REPOSITORY, and GITHUB_REF_NAME are required')
  process.exit(1)
}

process.stdout.write(`# ${tag}

## Container

The image is \`${image}\` (linux/amd64).

\`\`\`sh
podman pull ${image}
\`\`\`

Open https://127.0.0.1:4173. The certificate is self-signed. The first launch writes it to data/tls/cert.pem.

## npm

The command is \`dashboard\`. The name \`dashboard\` on the public npm registry already belongs to a different project, so install this package from the release tarball:

\`\`\`sh
npm install -g https://github.com/${repo}/releases/download/${tag}/${tgz}
\`\`\`

From a checkout:

\`\`\`sh
npm install -g .
\`\`\`
`)
