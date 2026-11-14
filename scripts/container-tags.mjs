import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const SEMVER = /^\d+\.\d+\.\d+$/

export function containerfileNodeVersion(source) {
  const match = source.match(/^ARG NODE_VERSION=(\d+)\s*$/m)
  if (!match) throw new Error('Containerfile is missing ARG NODE_VERSION')
  return match[1]
}

export function versionFromGitTag(tag) {
  const value = String(tag || '').trim()
  if (!value) throw new Error('No v* tag describes HEAD. Refusing to invent a version.')
  const match = /^v(\d+\.\d+\.\d+)$/.exec(value)
  if (!match) {
    throw new Error(`Nearest tag ${value} is not vMAJOR.MINOR.PATCH. Refusing to invent a version.`)
  }
  return match[1]
}

export function requireBuild(build) {
  const value = String(build ?? '').trim()
  if (!/^[1-9]\d*$/.test(value)) {
    throw new Error('GITHUB_RUN_NUMBER is required and must be a positive integer. Refusing to invent a build number.')
  }
  return value
}

export function resolveImageTags({ imageName, version, build }) {
  if (!imageName || !imageName.includes('/')) throw new Error('Missing image name')
  const image = imageName.toLowerCase()
  if (!SEMVER.test(String(version || ''))) {
    throw new Error('No vMAJOR.MINOR.PATCH tag describes HEAD. Refusing to invent a version.')
  }
  const run = requireBuild(build)
  return {
    version: String(version),
    build: run,
    image,
    publish: true,
    tags: [`${image}:${version}-${run}`, `${image}:latest`],
  }
}

export function formatGithubOutput(result) {
  return [
    `version=${result.version}`,
    `build=${result.build}`,
    `publish=${result.publish ? 'true' : 'false'}`,
    `image=${result.image}`,
    `tags=${result.tags.join(',')}`,
    '',
  ].join('\n')
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
    const version = versionFromGitTag(process.env.GIT_TAG || '')
    const build = requireBuild(process.env.GITHUB_RUN_NUMBER || '')
    const result = resolveImageTags({ imageName, version, build })
    const output = formatGithubOutput(result)
    process.stdout.write(output)
    if (process.env.GITHUB_OUTPUT) fs.appendFileSync(process.env.GITHUB_OUTPUT, output)
  } catch (error) {
    console.error(error.message || error)
    process.exit(1)
  }
}
