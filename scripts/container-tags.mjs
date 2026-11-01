import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const VERSION = /^(\d+)\.(\d+)\.(\d+)$/

export function containerfileNodeVersion(source) {
  const match = source.match(/^ARG NODE_VERSION=(\d+)\s*$/m)
  if (!match) throw new Error('Containerfile is missing ARG NODE_VERSION')
  return match[1]
}

export function resolveImageTags({ imageName, ref, refName, sha, version, event = '' }) {
  if (!imageName || !imageName.includes('/')) throw new Error('Missing image name')
  const parsed = VERSION.exec(version)
  if (!parsed) throw new Error(`Invalid package.json version: ${version}`)
  const [, major, minor] = parsed
  const image = imageName.toLowerCase()
  const base = { version, image }

  if (ref.startsWith('refs/tags/v')) {
    const tag = refName.startsWith('v') ? refName.slice(1) : refName
    if (tag !== version) throw new Error(`Tag v${tag} does not match package.json version ${version}`)
    return {
      ...base,
      publish: true,
      tags: [`${image}:${version}`, `${image}:${major}.${minor}`, `${image}:${major}`, `${image}:latest`],
    }
  }

  if (ref === 'refs/heads/master' || ref === 'refs/heads/main') {
    if (!sha || sha.length < 12) throw new Error('Missing commit SHA')
    return {
      ...base,
      publish: true,
      tags: [`${image}:edge`, `${image}:sha-${sha.slice(0, 12)}`],
    }
  }

  // A manual run of publish-container is allowed to push from any branch.
  if (event === 'workflow_dispatch') {
    if (!sha || sha.length < 12) throw new Error('Missing commit SHA')
    return {
      ...base,
      publish: true,
      tags: [`${image}:sha-${sha.slice(0, 12)}`],
    }
  }

  return { ...base, publish: false, tags: [] }
}

export function formatGithubOutput(result) {
  return [
    `version=${result.version}`,
    `publish=${result.publish ? 'true' : 'false'}`,
    `image=${result.image}`,
    `tags=${result.tags.join(',')}`,
    '',
  ].join('\n')
}

function readVersion() {
  const file = fileURLToPath(new URL('../package.json', import.meta.url))
  return JSON.parse(fs.readFileSync(file, 'utf8')).version
}

function assertNodeVersion(expected) {
  if (!expected) return
  const containerfile = fs.readFileSync(fileURLToPath(new URL('../Containerfile', import.meta.url)), 'utf8')
  const actual = containerfileNodeVersion(containerfile)
  if (actual !== expected) {
    throw new Error(`Containerfile NODE_VERSION=${actual} does not match NODE_VERSION=${expected}`)
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isMain) {
  try {
    assertNodeVersion(process.env.NODE_VERSION)
    const imageName = process.env.IMAGE_NAME || (process.env.GITHUB_REPOSITORY ? `ghcr.io/${process.env.GITHUB_REPOSITORY}` : '')
    const result = resolveImageTags({
      imageName,
      ref: process.env.GITHUB_REF || '',
      refName: process.env.GITHUB_REF_NAME || '',
      sha: process.env.GITHUB_SHA || '',
      version: readVersion(),
      event: process.env.GITHUB_EVENT_NAME || '',
    })
    const output = formatGithubOutput(result)
    process.stdout.write(output)
    if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, output)
  } catch (error) {
    console.error(error.message || error)
    process.exit(1)
  }
}
