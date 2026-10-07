const tgz = process.env.TGZ_NAME
const repo = process.env.GITHUB_REPOSITORY
const tag = process.env.GITHUB_REF_NAME
if (!tgz || !repo || !tag) {
  console.error('TGZ_NAME, GITHUB_REPOSITORY, and GITHUB_REF_NAME are required')
  process.exit(1)
}

process.stdout.write(`# ${tag}

## macOS binary

\`dashboard-macos\` is one Apple silicon binary. Node.js is not required.

\`\`\`sh
chmod +x dashboard-macos
xattr -d com.apple.quarantine dashboard-macos
./dashboard-macos
\`\`\`

Then open http://127.0.0.1:4173

The binary is ad-hoc signed. The first launch may still need approval in System Settings → Privacy & Security.

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
