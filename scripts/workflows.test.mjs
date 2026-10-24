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
    expect(read('container.yml')).not.toMatch(/npm ci|npm test/)
    for (const name of files()) {
      expect(read(name), name).not.toMatch(/docker/i)
      expect(read(name), name).not.toMatch(/\b(dashboard|ernaehrung)\b/)
    }
    expect(jobs(read('container.yml')).image).toContain('packages: write')
    expect(calls(read('ci.yml'))).not.toContain('./.github/workflows/container-image.yml')
    expect(calls(read('release.yml'))).not.toContain('./.github/workflows/container-image.yml')
  })
})

describe('host test workflow', () => {
  const source = read('host-test.yml')

  it('runs the Linux host checks once on Node 24 via make', () => {
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source).toContain('runs-on: ubuntu-26.04')
    expect(source).toContain('actions/checkout@v7')
    expect(source.match(/^\s*run: make host-checks\s*$/m)).toHaveLength(1)
    expect(source).not.toMatch(/docker/i)
    expect(source).not.toContain('actions/setup-node')
    expect(source).not.toMatch(/npm ci|npm test|npm run package:binary|npm pack/)
  })
})

describe('container image workflow', () => {
  const source = read('container-image.yml')
  const imageJobs = jobs(source)

  it('builds once, smokes that image, and pushes it only when publishing', () => {
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source).not.toMatch(/docker/i)
    expect(source).not.toContain('actions/setup-node')
    expect(source).not.toMatch(/npm ci|npm test|npm run build/)
    expect(source).toContain('github.event.repository.name')
    expect(source.match(/^\s*run: make resolve-ghcr-tags\s*$/m)).toHaveLength(1)
    expect(source.match(/^\s*run: make ci-image\s*$/m)).toHaveLength(1)
    expect(imageJobs.build.match(/^\s*run: make ci-image\s*$/m)).toHaveLength(1)
    expect(imageJobs.build).not.toContain('make resolve-ghcr-tags')
    expect(imageJobs.build).not.toContain('make image\n')
    expect(imageJobs.build).toContain('Build the image once and smoke it')
    expect(imageJobs.build).toContain("success() && needs.resolve.outputs.publish == 'true'")
    expect(imageJobs.build).toContain('run: make image-save')
    expect(imageJobs.build).toContain('actions/upload-artifact@v7')
    expect(imageJobs.publish).toContain("success() && needs.resolve.outputs.publish == 'true'")
    expect(imageJobs.publish).toContain('actions/download-artifact@v8')
    expect(imageJobs.publish).toContain('run: make image-load')
    expect(imageJobs.publish).toContain('podman login')
    expect(imageJobs.publish).toContain('--password-stdin')
    expect(imageJobs.publish).toContain('run: make image-push')
    expect(imageJobs.publish).not.toContain('make ci-image')
  })

  it('grants packages: write only on the publish job', () => {
    expect(imageJobs.resolve).not.toContain('packages: write')
    expect(imageJobs.build).not.toContain('packages: write')
    expect(imageJobs.publish).toContain('packages: write')
    expect(imageJobs.resolve).toContain('runs-on: ubuntu-26.04')
    expect(imageJobs.build).toContain('runs-on: ubuntu-26.04')
    expect(imageJobs.publish).toContain('runs-on: ubuntu-26.04')
  })
})

describe('release workflow', () => {
  const source = read('release.yml')
  const releaseJobs = jobs(source)

  it('keeps the macOS binary, npm tarball, GitHub release, and optional npm publish', () => {
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source).toContain('runs-on: macos-latest')
    expect(source).toContain('github.event.repository.name')
    expect(releaseJobs.macos).toContain('actions/setup-node@v7')
    expect(releaseJobs.macos).toContain('make macos-binary')
    expect(releaseJobs.macos).toContain('actions/upload-artifact@v7')
    expect(releaseJobs['npm-package']).toContain('runs-on: ubuntu-26.04')
    expect(releaseJobs['npm-package']).toContain('run: make npm-tarball')
    expect(releaseJobs['npm-package']).not.toMatch(/docker/i)
    expect(releaseJobs.release).toContain("startsWith(github.ref, 'refs/tags/v')")
    expect(releaseJobs.release).toContain('run: make release-assets')
    expect(releaseJobs.release).toContain('actions/download-artifact@v8')
    expect(releaseJobs.release).toContain('gh release create')
    expect(releaseJobs.release).toContain('gh release upload')
    expect(releaseJobs.release).toContain('contents: write')
    expect(releaseJobs.release).toContain('build/notes.md')
    expect(releaseJobs.release).toContain('build/SHA256SUMS')
    expect(releaseJobs['publish-npm']).toContain("vars.NPM_PUBLISH == 'true'")
    expect(releaseJobs['publish-npm']).toContain('actions/setup-node@v7')
    expect(releaseJobs['publish-npm']).toContain('registry-url: https://registry.npmjs.org')
    expect(releaseJobs['publish-npm']).toContain('id-token: write')
    expect(releaseJobs['publish-npm']).toContain('make npm-publish')
    expect(source).not.toMatch(/\bnpm ci\b|\bnpm test\b|\bnpm pack\b|\bnpm publish\b|\bsha256sum\b|\bbuild-binary\b/)
  })
})

function makefile() {
  return readFileSync(new URL('../Makefile', import.meta.url), 'utf8')
}

function targetChunk(source, name) {
  const lines = source.split('\n')
  const start = lines.findIndex((line) => line.startsWith(`${name}:`))
  if (start === -1) throw new Error(`missing target ${name}`)
  const body = [lines[start]]
  for (const line of lines.slice(start + 1)) {
    if (/^[a-zA-Z0-9_-]+:/.test(line)) break
    body.push(line)
  }
  return body.join('\n')
}

describe('Makefile CI targets', () => {
  const source = makefile()
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))

  it('uses Podman in CI and on a laptop', () => {
    expect(source).toContain('NODE_VERSION ?= 24')
    expect(source).toContain('CI_IMAGE ?= localhost/$(NAME):ci')
    expect(source).toContain(`NAME ?= ${pkg.name}`)
    expect(source).not.toMatch(/docker/i)
    expect(source).not.toContain('CONTAINER')
    expect(targetChunk(source, 'help')).toContain('Match CI')
    expect(targetChunk(source, 'help')).toContain('Podman is the only container engine, on a laptop and in CI.')
  })

  it('keeps the product block and uses it', () => {
    for (const key of ['NAME', 'PORT', 'DEV_PORT', 'DATA_FILE', 'DATA_ENV', 'API_PATH', 'SMOKE_NEEDLE']) {
      expect(source, key).toMatch(new RegExp(`^${key} \\?= \\S`, 'm'))
    }
    expect(targetChunk(source, 'help')).toContain('$(DEV_PORT)')
    expect(targetChunk(source, 'help')).toContain('$(DATA_FILE)')
    expect(targetChunk(source, 'run')).toContain('$(DATA_ENV)=/app/$(DATA_FILE)')
    const smoke = targetChunk(source, 'smoke-image')
    expect(smoke).toContain('$(API_PATH)')
    expect(smoke).toContain('$(SMOKE_NEEDLE)')
  })

  it('keeps local build and run on Podman without host Node', () => {
    expect(targetChunk(source, 'build')).toContain('podman build')
    expect(targetChunk(source, 'build')).not.toContain('npm')
    expect(targetChunk(source, 'run')).toContain('podman run')
    expect(targetChunk(source, 'run')).not.toContain('npm')
    expect(source).toContain('ci: host-checks ci-image')
  })

  it('runs the Linux host checks in one Node image', () => {
    expect(source).toContain(
      'host-checks: check-tag npm-ci test linux-binary smoke-linux-binary pack-smoke',
    )
    expect(targetChunk(source, 'check-tag')).toContain('refs/tags/v')
    expect(targetChunk(source, 'npm-ci')).toContain('$(NODE_RUN) npm ci')
    expect(targetChunk(source, 'test')).toContain('$(NODE_RUN) npm test')
    expect(targetChunk(source, 'linux-binary')).toContain('$(NODE_RUN) npm run package:binary')
    expect(targetChunk(source, 'smoke-linux-binary')).toContain(
      '$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME)',
    )
    const pack = targetChunk(source, 'pack-smoke')
    expect(pack).toContain('npm pack --ignore-scripts --pack-destination')
    expect(pack).toContain('node scripts/smoke-binary.mjs')
    expect(source.match(/\$\(NODE_RUN\) npm ci/g)).toHaveLength(1)
  })

  it('builds the CI image once and smokes that image', () => {
    expect(source).toContain('ci-image: smoke-image')
    expect(source).toContain('smoke-image: image')
    const image = targetChunk(source, 'image')
    expect(image).toContain('podman build')
    expect(image).toContain('-t "$(CI_IMAGE)"')
    expect(image).not.toMatch(/\bpush\b/)
    expect(targetChunk(source, 'smoke-image')).toContain('id="root"')
    expect(targetChunk(source, 'smoke-image')).toContain('podman run')
    expect(targetChunk(source, 'smoke-image')).not.toContain('podman build')
    expect(targetChunk(source, 'resolve-ghcr-tags')).toContain('node scripts/container-tags.mjs')
    expect(targetChunk(source, 'image-save')).toContain('podman save -o $(NAME)-image.tar')
    expect(targetChunk(source, 'image-load')).toContain('podman load -i')
    const push = targetChunk(source, 'image-push')
    expect(push).toContain('Refusing to push')
    expect(push).toContain('podman push')
  })

  it('keeps release commands that can run locally, and gates publish', () => {
    const macos = targetChunk(source, 'macos-binary')
    expect(macos).toContain('Darwin')
    expect(macos).toContain('node scripts/build-binary.mjs --macos')
    expect(macos).toContain('lipo -archs build/$(NAME)-macos')
    expect(macos).not.toContain('NODE_RUN')
    const tarball = targetChunk(source, 'npm-tarball')
    expect(tarball).toContain('npm pack --pack-destination build')
    expect(tarball).not.toContain('ignore-scripts')
    expect(targetChunk(source, 'release-assets')).toContain('node scripts/release-notes.mjs')
    expect(targetChunk(source, 'release-assets')).toContain('SHA256SUMS')
    const publish = targetChunk(source, 'npm-publish')
    expect(publish).toContain('NPM_PUBLISH')
    expect(publish).toContain('npm publish --access public --provenance')
  })
})
