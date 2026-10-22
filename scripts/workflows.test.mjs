import { readFileSync, readdirSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const workflowDir = new URL('../.github/workflows/', import.meta.url)

function read(name) {
  return readFileSync(new URL(name, workflowDir), 'utf8')
}

function files() {
  return readdirSync(workflowDir)
    .filter((name) => name.endsWith('.yml'))
    .sort()
}

function block(source, key) {
  const lines = source.split('\n')
  const start = lines.findIndex((line) => line === `${key}:`)
  if (start === -1) throw new Error(`missing ${key}`)
  const body = []
  for (const line of lines.slice(start + 1)) {
    if (/^\S/.test(line)) break
    body.push(line)
  }
  return body.join('\n')
}

function triggers(source) {
  const on = block(source, 'on')
  return {
    workflow_call: /\bworkflow_call:/.test(on),
    workflow_dispatch: /\bworkflow_dispatch:/.test(on),
    pull_request: /\bpull_request:/.test(on),
    everyBranch: /branches:[\s\S]*?['"]\*\*['"]/.test(on),
    masterOnly: /branches:\s*\[master\]/.test(on),
    tags: /tags:[\s\S]*?['"]v\*\.\*\.\*['"]/.test(on),
  }
}

function calls(source) {
  return [...source.matchAll(/^\s*uses:\s*(\.\/\.github\/workflows\/[\w.-]+)/gm)].map((match) => match[1])
}

function jobs(source) {
  const lines = block(source, 'jobs').split('\n')
  const chunks = []
  let current = null
  for (const line of lines) {
    if (/^ {2}[A-Za-z0-9_-]+:\s*$/.test(line)) {
      if (current) chunks.push(current)
      current = [line]
    } else if (current) current.push(line)
  }
  if (current) chunks.push(current)
  return Object.fromEntries(chunks.map((chunk) => [chunk[0].trim().replace(/:$/, ''), chunk.join('\n')]))
}

const entryPoints = ['ci.yml', 'container.yml', 'release.yml']

describe('workflow entry points', () => {
  it('keeps CI, Container, and Release as the only event entry points', () => {
    expect(files()).toEqual([
      'ci.yml',
      'container-image.yml',
      'container.yml',
      'host-test.yml',
      'release.yml',
    ])
    for (const name of ['host-test.yml', 'container-image.yml']) {
      const on = triggers(read(name))
      expect(on.workflow_call).toBe(true)
      expect(on.pull_request).toBe(false)
      expect(on.everyBranch).toBe(false)
      expect(on.tags).toBe(false)
      expect(on.workflow_dispatch).toBe(false)
    }
  })

  it('runs host npm ci and npm test from one caller per event', () => {
    const callers = entryPoints.filter((name) => calls(read(name)).includes('./.github/workflows/host-test.yml'))
    expect(callers).toEqual(['ci.yml', 'release.yml'])

    const ci = triggers(read('ci.yml'))
    expect(ci.pull_request).toBe(false)
    expect(ci.everyBranch).toBe(true)
    expect(ci.masterOnly).toBe(false)
    expect(ci.tags).toBe(false)
    expect(ci.workflow_dispatch).toBe(true)

    const release = triggers(read('release.yml'))
    expect(release.tags).toBe(true)
    expect(release.workflow_dispatch).toBe(true)
    expect(release.pull_request).toBe(false)
    expect(release.everyBranch).toBe(false)
    expect(release.masterOnly).toBe(false)

    expect(calls(read('container.yml'))).not.toContain('./.github/workflows/host-test.yml')
    expect(read('ci.yml')).not.toMatch(/npm ci|npm test|npm run package:binary/)
    expect(read('release.yml')).not.toMatch(/npm test|npm run package:binary/)
  })

  it('builds the container image from the Container workflow only', () => {
    const callers = entryPoints.filter((name) => calls(read(name)).includes('./.github/workflows/container-image.yml'))
    expect(callers).toEqual(['container.yml'])

    const container = triggers(read('container.yml'))
    expect(container.pull_request).toBe(false)
    expect(container.everyBranch).toBe(true)
    expect(container.masterOnly).toBe(false)
    expect(container.tags).toBe(true)
    expect(container.workflow_dispatch).toBe(true)
    expect(read('container.yml')).not.toMatch(/npm ci|npm test|docker\/build-push-action/)
    expect(jobs(read('container.yml')).image).toContain('packages: write')
    expect(calls(read('ci.yml'))).not.toContain('./.github/workflows/container-image.yml')
    expect(calls(read('release.yml'))).not.toContain('./.github/workflows/container-image.yml')
  })
})

describe('host test workflow', () => {
  const source = read('host-test.yml')

  it('installs, tests, and packs once on Node 24', () => {
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source.match(/^\s*- run: npm ci\s*$/gm)).toHaveLength(1)
    expect(source.match(/^\s*- run: npm test\s*$/gm)).toHaveLength(1)
    expect(source).toContain('npm run package:binary')
    const packCommands = [...source.matchAll(/^\s*npm pack\b.*$/gm)].map((match) => match[0].trim())
    expect(packCommands).toEqual(['npm pack --ignore-scripts --pack-destination "$stage"'])
    expect(source).toContain("startsWith(github.ref, 'refs/tags/v')")
  })
})

describe('container image workflow', () => {
  const source = read('container-image.yml')
  const imageJobs = jobs(source)

  it('builds once, smokes the loaded image, and pushes that image only when publishing', () => {
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source.match(/docker\/build-push-action@/g)).toHaveLength(1)
    expect(source).toContain('push: false')
    expect(source).toContain('load: true')
    expect(source).not.toContain('push: true')
    expect(source).toContain('node scripts/container-tags.mjs')
    expect(source).not.toMatch(/npm ci|npm test|npm run build/)
    expect(imageJobs.build).toContain('Smoke test the image')
    expect(imageJobs.build).toContain("success() && needs.resolve.outputs.publish == 'true'")
    expect(imageJobs.build).toContain('docker save dashboard:ci')
    expect(imageJobs.publish).toContain("success() && needs.resolve.outputs.publish == 'true'")
    expect(imageJobs.publish).toContain('docker load --input image/dashboard-image.tar')
    expect(imageJobs.publish).toContain('docker push "$tag"')
    expect(imageJobs.publish).not.toContain('docker/build-push-action')
  })

  it('grants packages: write only on the publish job', () => {
    expect(imageJobs.resolve).not.toContain('packages: write')
    expect(imageJobs.build).not.toContain('packages: write')
    expect(imageJobs.publish).toContain('packages: write')
  })
})

describe('release workflow', () => {
  const source = read('release.yml')

  it('keeps the macOS binary, npm tarball, GitHub release, and optional npm publish', () => {
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source).toContain('runs-on: macos-latest')
    expect(source).toContain('node scripts/build-binary.mjs --macos')
    expect(source).toContain('npm pack --pack-destination build')
    expect(source).toContain('gh release create')
    expect(source).toContain("vars.NPM_PUBLISH == 'true'")
    expect(source).toContain('npm publish --access public --provenance')
    expect(source).toContain('contents: write')
  })
})
