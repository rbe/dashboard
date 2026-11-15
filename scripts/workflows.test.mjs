import { createHash } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { existsSync, readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const SDLC_MK_SHA256 = '45c6cf23664d030c61f0fedd2d0639cd9dc2dc7bb03c14167dce61fed9d495d6'

const workflowDir = new URL('../.github/workflows/', import.meta.url)
const jobNames = [
  'setup',
  'build',
  'test',
  'docs',
  'publish-container',
  'report',
]

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

function makeCalls(chunk) {
  return [...chunk.matchAll(/^\s*(?:- )?run: make (\S+)\s*$/gm)].map((match) => match[1])
}

function runLines(source) {
  return [...source.matchAll(/^\s*(?:- )?run: (.+)$/gm)].map((match) => `run: ${match[1].trim()}`)
}

function uploadBlocks(source) {
  const lines = source.split('\n')
  const blocks = []
  for (let i = 0; i < lines.length; i += 1) {
    if (!/uses: actions\/upload-artifact@/.test(lines[i])) continue
    const body = [lines[i]]
    for (let j = i + 1; j < lines.length; j += 1) {
      if (/^\s*- (?:uses:|name:|run:)/.test(lines[j])) break
      if (/^ {2}\S/.test(lines[j])) break
      body.push(lines[j])
    }
    blocks.push(body.join('\n'))
  }
  return blocks
}

describe('workflow', () => {
  const source = read('ci.yml')
  const pipeline = jobs(source)
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))

  it('keeps app CI in ci.yml and does not call another workflow', () => {
    expect(files()).toEqual(['ci.yml', 'publish-client.yml'])
    const on = triggers(source)
    expect(on.workflow_call).toBe(false)
    expect(on.workflow_dispatch).toBe(true)
    expect(on.pull_request).toBe(false)
    expect(on.everyBranch).toBe(true)
    expect(on.masterOnly).toBe(false)
    expect(on.tags).toBe(false)
    expect(block(source, 'on')).not.toMatch(/\btags:/)
    expect(source).toContain("github.ref != format('refs/heads/{0}', github.event.repository.default_branch)")
    expect(source).not.toContain("github.ref_type == 'branch'")
    expect(source).not.toMatch(/uses:\s*\.\/\.github\/workflows\//)
    expect(source).not.toMatch(/\bhost-checks\b|\bci-image\b|\bnpm-tarball\b|\bmacos-binary\b|\bmacos-package\b|\bnpm-publish\b|\bpublish-github\b|\bnpm-package\b|\bpublish-npm\b/)
    expect(source).not.toMatch(/\bNPM_PUBLISH\b|\bNPM_TOKEN\b|\bid-token\b/)
    expect(source).not.toContain('actions/setup-node')
    expect(source).not.toContain('macos-latest')
    expect(source).not.toContain('dashboard-macos')
    expect(source).not.toMatch(/\bgh release\b|action-gh-release|upload-release-asset|softprops/)
    expect(source).not.toContain('publish-client')
    expect(source).not.toContain('client-v')
    expect(source).not.toContain('@rbe/dashboard-client')
    expect(source).not.toContain('SHA256SUMS')
    expect(source).not.toMatch(/contents:\s*write/)
    expect(source).not.toMatch(/docker/i)
    expect(source).not.toMatch(/\bnpm ci\b|\bnpm test\b|\bnpm pack\b|\bnpm publish\b/)
    expect(source).not.toMatch(/\bernaehrung\b/)
  })

  it('names the jobs in pipeline order and calls the matching make targets', () => {
    expect(Object.keys(pipeline)).toEqual(jobNames)
    const optionsLine = source.match(/options: \[([^\]]+)\]/)
    expect(optionsLine).not.toBeNull()
    expect(optionsLine[1].split(',').map((item) => item.trim())).toEqual(jobNames)
    for (const name of jobNames) {
      const calls = makeCalls(pipeline[name])
      if (name === 'setup') {
        expect(calls, name).toEqual(['cleanup-actions-artifacts', 'setup'])
      } else if (name === 'publish-container') {
        expect(calls, name).toEqual(['login', 'publish-container', 'cleanup-container-versions'])
      } else {
        expect(calls, name).toEqual([name])
      }
    }
    expect(source.match(/run: make cleanup-container-versions/g)).toEqual(['run: make cleanup-container-versions'])
    expect(source.match(/run: make cleanup-actions-artifacts/g)).toEqual(['run: make cleanup-actions-artifacts'])
    expect(source).not.toContain('prune-package-versions')
    expect(Object.keys(pipeline)).not.toContain('cleanup-container-versions')
    expect(Object.keys(pipeline)).not.toContain('prune-package-versions')
    for (const line of runLines(source)) {
      expect(line, line).toMatch(/^run: make [a-z0-9-]+$/)
    }
    expect(runLines(source).join('\n')).not.toMatch(/\btar\b|\btee\b|\bnpm\b|\bpodman\b|\bprintf\b/)
    expect(source).not.toMatch(/\bpodman\b/)
    expect(source).not.toMatch(/\bnpm\b/)
    expect(source).not.toMatch(/^\s*shell:/m)
    expect(source).not.toContain('podman login')
    expect(source).toContain('run: make login')
  })

  it('keeps the image name in one place and does not invent a version', () => {
    expect(source.match(/ghcr\.io\/rbe\/dashboard/g)).toEqual(['ghcr.io/rbe/dashboard'])
    expect(source.match(/^ {2}IMAGE_NAME:/gm)).toHaveLength(1)
    expect(source).not.toMatch(/^ {2}VERSION:/m)
    expect(source).not.toContain(pkg.version)
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source).toContain('SDLC_DEFAULT_BRANCH: ${{ github.event.repository.default_branch }}')
    expect(source).toContain('actions/checkout@v7')
    expect(source).toContain('actions/upload-artifact@v7')
    expect(source).toContain('actions/download-artifact@v8')
    expect(source).not.toMatch(/actions\/(checkout|upload-artifact|setup-node)@v[0-6]\b/)
    expect(source).not.toMatch(/actions\/download-artifact@v[0-7]\b/)
  })

  it('passes artifacts forward and does not rebuild them in a later job', () => {
    expect(pipeline.setup).toContain('name: deps')
    expect(pipeline.setup).toContain('path: build/deps/node_modules.tar')
    expect(pipeline.setup).toContain('actions: write')
    expect(pipeline.setup).not.toMatch(/^ {4}if:/m)
    const setupText = pipeline.setup
    const checkoutAt = setupText.indexOf('actions/checkout')
    const cleanupAt = setupText.indexOf('run: make cleanup-actions-artifacts')
    const setupAt = setupText.indexOf('run: make setup')
    const uploadAt = setupText.indexOf('actions/upload-artifact')
    expect(checkoutAt).toBeGreaterThan(-1)
    expect(cleanupAt).toBeGreaterThan(checkoutAt)
    expect(setupAt).toBeGreaterThan(cleanupAt)
    expect(uploadAt).toBeGreaterThan(setupAt)
    expect(pipeline.build).toContain('name: deps')
    expect(pipeline.build).toContain('name: image')
    expect(pipeline.build).toContain('path: build/image')
    expect(pipeline.build).not.toContain('name: dist')
    expect(pipeline.build).not.toContain('make setup')
    expect(source).not.toContain('name: dist')
    expect(pipeline.test).toContain('name: deps')
    expect(pipeline.test).toContain('name: report-test')
    expect(pipeline.test).toContain('build/test-results')
    expect(pipeline.test).toContain('build/coverage')
    expect(pipeline.test).toContain('build/logs')
    expect(pipeline.test).not.toContain('needs.test.outputs.reports')
    expect(pipeline.report).toContain('needs: [setup, build, test, docs, publish-container]')
    expect(pipeline.report).toContain('if: ${{ !cancelled() }}')
    expect(pipeline.report).toContain('pattern: report-*')
    expect(pipeline.report).toContain('path: build/inputs')
    expect(pipeline.report).toContain('name: report')
    expect(pipeline.report).toContain('path: build/report')
    expect(pipeline.report).toContain('retention-days: 14')
    expect(pipeline.report).not.toContain('macos-package')
    expect(pipeline.report).not.toContain("needs.publish-container.result == 'success'")
    expect(pipeline.report).not.toContain("needs.publish-container.result == 'failure'")
    expect(pipeline.report).not.toContain("needs.publish-container.result == 'skipped'")
    expect(pipeline.report).not.toContain('gh release')
    expect(pipeline['publish-container']).toContain('name: image')
    expect(pipeline['publish-container']).toContain('path: build/image')
    expect(pipeline['publish-container']).not.toMatch(/make (build|image|ci-image|setup)\b/)
    expect(pipeline['publish-container']).not.toContain('podman build')
    expect(pipeline['publish-container']).toContain('name: report-publish-container')
    expect(pipeline['publish-container']).not.toContain('gh release')
    expect(pipeline['publish-container']).not.toContain('name: docs')
    expect(pipeline.docs).toContain('needs: setup')
    expect(pipeline.docs).toContain('name: docs')
    expect(pipeline.docs).toContain('path: build/docs')
    expect(pipeline.docs).toContain('retention-days: 14')
    expect(pipeline.docs).toContain('if-no-files-found: ignore')
    expect(pipeline.docs).not.toContain('needs: build')
    expect(pipeline.docs).not.toContain('needs: test')
    expect(pipeline.docs).not.toContain('needs: [')
    const keptLong = new Set(['report', 'docs'])
    const blocks = uploadBlocks(source)
    expect(blocks.length).toBeGreaterThanOrEqual(9)
    for (const block of blocks) {
      const name = block.match(/\bname:\s*(\S+)/)
      const days = block.match(/retention-days:\s*(\d+)/)
      expect(name, block).not.toBeNull()
      expect(days, name?.[1] ?? block).not.toBeNull()
      const retention = Number(days[1])
      expect(retention).toBeLessThanOrEqual(14)
      if (keptLong.has(name[1])) expect(retention, name[1]).toBe(14)
      else expect(retention, name[1]).toBe(1)
    }
  })

  it('publishes the image from the default branch, or from a manual run of that job', () => {
    expect(pipeline['publish-container']).toContain("inputs.job == 'publish-container'")
    expect(pipeline['publish-container']).toContain("github.event_name == 'workflow_dispatch'")
    expect(pipeline['publish-container']).toContain("github.event_name == 'push'")
    expect(pipeline['publish-container']).toContain("github.event.repository.default_branch")
    expect(pipeline['publish-container']).not.toContain("github.ref == 'refs/heads/master'")
    expect(pipeline['publish-container']).not.toContain("github.ref == 'refs/heads/main'")
    expect(pipeline['publish-container']).not.toContain('refs/tags')
    expect(pipeline['publish-container']).not.toContain('refs/heads/**')
    expect(pipeline['publish-container']).toContain("needs.test.result == 'success'")
    expect(pipeline['publish-container']).toContain("needs.build.result == 'success'")
    expect(pipeline['publish-container']).toContain('needs: [build, test]')
    expect(pipeline['publish-container']).not.toContain('needs: [build, test, report]')
    expect(pipeline['publish-container']).not.toContain('docs')
    expect(pipeline['publish-container']).toContain('packages: write')
    expect(pipeline['publish-container']).toContain('run: make login')
    expect(pipeline['publish-container']).toContain('REGISTRY_USER: ${{ github.actor }}')
    expect(pipeline['publish-container']).toContain('REGISTRY_TOKEN: ${{ github.token }}')
    expect(pipeline['publish-container']).not.toContain('podman login')
    expect(pipeline['publish-container']).not.toContain('--password-stdin')
    expect(pipeline['publish-container']).not.toContain('dashboard-macos')
    expect(pipeline['publish-container']).toContain('fetch-depth: 0')
    expect(pipeline['publish-container']).toContain('fetch-tags: true')
    expect(source.match(/fetch-depth: 0/g)).toHaveLength(1)
    expect(source.match(/fetch-tags: true/g)).toHaveLength(1)
    expect(pipeline['publish-container']).not.toContain('edge')
    expect(pipeline['publish-container']).not.toContain('sha-')
    const publishLines = pipeline['publish-container'].split('\n')
    const pruneLine = publishLines.findIndex((line) => line.includes('run: make cleanup-container-versions'))
    const pushLine = publishLines.findIndex((line) => line.includes('run: make publish-container'))
    expect(pushLine).toBeGreaterThan(-1)
    expect(pruneLine).toBeGreaterThan(pushLine)
    const pruneStep = publishLines.slice(pruneLine, pruneLine + 4).join('\n')
    expect(pruneStep).toContain('GH_TOKEN: ${{ github.token }}')
    expect(pruneStep).not.toMatch(/\bif:/)
    const alwaysLines = publishLines.flatMap((line, index) => (line.includes('if: always()') ? [index] : []))
    expect(alwaysLines.length).toBeGreaterThan(0)
    expect(Math.min(...alwaysLines)).toBeGreaterThan(pruneLine)
    expect(source).not.toContain('secrets.')
    for (const name of jobNames) {
      if (name === 'publish-container') continue
      expect(pipeline[name], name).not.toContain('cleanup-container-versions')
    }
    expect(source.match(/packages: write/g)).toHaveLength(1)
    expect(source).not.toMatch(/id-token:\s*write/)
    expect(source).not.toMatch(/contents:\s*write/)
    const order = Object.keys(pipeline)
    expect(order.at(-1)).toBe('report')
    expect(order.indexOf('docs')).toBeGreaterThan(order.indexOf('test'))
    expect(order.indexOf('docs')).toBeLessThan(order.indexOf('publish-container'))
    expect(order.indexOf('publish-container')).toBeLessThan(order.indexOf('report'))
  })

  it('runs build, test, and docs beside each other, and report still runs when publish is skipped or fails', () => {
    expect(pipeline.build).toContain('needs: setup')
    expect(pipeline.test).toContain('needs: setup')
    expect(pipeline.docs).toContain('needs: setup')
    expect(pipeline.test).not.toContain('needs: build')
    expect(pipeline.build).not.toContain('needs: test')
    expect(pipeline.docs).not.toContain('needs: build')
    expect(pipeline.docs).not.toContain('needs: test')
    expect(pipeline.test).toContain('success()')
    expect(pipeline.build).toContain('success()')
    expect(pipeline.docs).toContain('success()')
    expect(pipeline.build).toContain('["build","publish-container","report"]')
    expect(pipeline.test).toContain('["test","publish-container","report"]')
    expect(pipeline.docs).toContain('["docs","report"]')
    expect(pipeline.docs).not.toContain('publish-container')
    expect(pipeline['publish-container']).not.toContain("inputs.job == 'report'")
    expect(pipeline.report).toContain('needs: [setup, build, test, docs, publish-container]')
    expect(pipeline.report).toContain('if: ${{ !cancelled() }}')
    for (const name of ['setup', 'build', 'test', 'docs', 'publish-container']) {
      expect(pipeline[name], name).toContain(`name: report-${name}`)
      expect(pipeline[name], name).toContain('build/logs')
    }
    for (const name of jobNames) {
      expect(pipeline[name], name).toContain('runs-on: ubuntu-26.04')
    }
  })
})

describe('client publish workflow', () => {
  const source = read('publish-client.yml')
    const client = JSON.parse(readFileSync(new URL('../client/package.json', import.meta.url), 'utf8'))

  it('packs the client, cuts a release, and publishes to GitHub Packages', () => {
    expect(client.name).toBe('@rbe/dashboard-client')
    const on = triggers(source)
    expect(on.workflow_dispatch).toBe(true)
    expect(on.pull_request).toBe(false)
    expect(on.workflow_call).toBe(false)
    expect(on.everyBranch).toBe(false)
    expect(on.tags).toBe(false)
    expect(source).toContain("tags:")
    expect(source).toContain("'client-v*'")
    expect(source).toContain('runs-on: ubuntu-26.04')
    expect(source).toContain('actions/checkout@v7')
    expect(source).toContain('actions/setup-node@v7')
    expect(source).toContain('node-version: "24"')
    expect(source).toContain('https://npm.pkg.github.com')
    expect(source).toContain('scope: "@rbe"')
    expect(source).toContain('working-directory: client')
    expect(source).toContain('npm ci')
    expect(source).toContain('npm test')
    expect(source).toContain('npm pack')
    expect(source).toContain('npm publish')
    expect(source).toContain('gh release create')
    expect(source).toContain('@rbe/dashboard-client')
    expect(source).toContain('contents: write')
    expect(source).toContain('packages: write')
    expect(source).toContain('NODE_AUTH_TOKEN: ${{ secrets.GITHUB_TOKEN }}')
    expect(source).toContain('GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}')
    expect(source).toContain('Refusing to invent a version.')
    expect(source).toContain('client-v${version}')
    expect(source).not.toMatch(/\bmake\b/)
    expect(source).not.toMatch(/docker|podman|ghcr\.io/i)
    expect(source).not.toContain('publish-container')
    expect(source).not.toContain('workflow_call')
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
  const sdlc = readFileSync(new URL('../sdlc.mk', import.meta.url))

  it('includes the shared makefile byte for byte', () => {
    expect(createHash('sha256').update(sdlc).digest('hex')).toBe(SDLC_MK_SHA256)
    const includeAt = source.indexOf('\ninclude sdlc.mk\n')
    expect(includeAt).toBeGreaterThan(-1)
    expect(source.slice(0, includeAt)).not.toMatch(/^[a-zA-Z0-9_-]+:/m)
    for (const name of ['help', 'version', 'ci', 'report', 'cleanup-container-versions', 'cleanup-github-releases', 'cleanup-actions-artifacts', 'host-checks', 'git-version', 'prune-package-versions']) {
      expect(source, name).not.toMatch(new RegExp(`^${name}:`, 'm'))
    }
    expect(source).toContain('IMAGE ?= $(IMAGE_NAME)')
    expect(source).toContain('PACKAGE ?= $(OWNER)/$(NAME)')
    expect(source).toContain('KEEP_VERSIONS ?= 2')
    expect(source).not.toContain('host-checks')
    expect(source).not.toContain('prune-package-versions')
    expect(source).not.toContain('scripts/prune-package-versions.mjs')
    expect(source).not.toContain('scripts/assemble-report.mjs')
    expect(source).not.toContain('publish-github')
    expect(sdlc.toString('utf8')).toContain('SDLC_CI ?= setup build test docs report')
    expect(sdlc.toString('utf8')).toContain('Refusing to invent a version.')
    expect(sdlc.toString('utf8')).toContain("git describe --tags --abbrev=0 --match 'v[0-9]*'")
    expect(sdlc.toString('utf8')).toContain('GITHUB_RUN_NUMBER must be a positive integer')
    expect(existsSync(new URL('../scripts/prune-package-versions.mjs', import.meta.url))).toBe(false)
  })

  it('uses Podman in CI and on a laptop', () => {
    expect(source).toContain('NODE_VERSION ?= 24')
    expect(source).toContain('CI_IMAGE ?= localhost/$(NAME):ci')
    expect(source).toContain(`NAME ?= ${pkg.name}`)
    expect(source).toContain('IMAGE_NAME ?= ghcr.io/$(OWNER)/$(NAME)')
    expect(source).not.toMatch(/docker/i)
    expect(source).not.toContain('CONTAINER')
    expect(source).toContain('Podman is the only container engine, on a laptop and in CI.')
    expect(source).toContain('$(DEV_PORT)')
    expect(source).toContain('$(DATA_FILE)')
    expect(sdlc.toString('utf8')).toContain('Match CI')
    expect(sdlc.toString('utf8')).toContain('Podman is the only container engine.')
  })

  it('keeps the product block and uses it', () => {
    for (const key of ['NAME', 'PORT', 'DEV_PORT', 'DATA_FILE', 'DATA_ENV', 'API_PATH', 'SMOKE_NEEDLE']) {
      expect(source, key).toMatch(new RegExp(`^${key} \\?= \\S`, 'm'))
    }
    expect(targetChunk(source, 'run')).toContain('$(DATA_ENV)=/app/$(DATA_FILE)')
    const smoke = targetChunk(source, 'smoke-image')
    expect(smoke).toContain('$(API_PATH)')
    expect(smoke).toContain('$(SMOKE_NEEDLE)')
    expect(smoke).toContain('id="root"')
  })

  it('keeps local build and run on Podman without host Node', () => {
    expect(targetChunk(source, 'image')).toContain('podman build')
    expect(targetChunk(source, 'image')).not.toContain('npm')
    expect(targetChunk(source, 'run')).toContain('podman run')
    expect(targetChunk(source, 'run')).not.toContain('npm')
    expect(source).not.toMatch(/^ci:/m)
    expect(source).not.toMatch(/^npm-package:/m)
    expect(source).not.toMatch(/^publish-npm:/m)
    expect(source).not.toMatch(/^publish-github:/m)
    expect(source).not.toContain('ci: host-checks')
  })

  it('splits the old host checks across the job targets', () => {
    for (const name of ['setup', 'build', 'test', 'docs', 'publish-container']) {
      expect(targetChunk(source, name), name).toContain(`$(call SDLC_LOG,${name},_${name})`)
    }
    expect(targetChunk(source, 'audit')).toContain('npm audit --audit-level=high || echo "npm audit reported advisories; continuing"')
    expect(targetChunk(source, '_setup')).toContain('npm-ci')
    expect(targetChunk(source, '_setup')).toContain('audit')
    expect(targetChunk(source, 'npm-ci')).toContain('$(NODE_RUN) npm ci')
    expect(targetChunk(source, '_test')).toContain('npm test -- --coverage')
    expect(targetChunk(source, '_test')).toContain('build/test-results/results.json')
    expect(targetChunk(source, '_build')).toContain('linux-binary')
    expect(targetChunk(source, '_build')).toContain('smoke-image')
    expect(targetChunk(source, '_build')).toContain('podman save -o build/image/$(NAME)-image.tar')
    expect(targetChunk(source, '_build')).not.toContain('npm ci')
    expect(targetChunk(source, 'linux-binary')).toContain('$(NODE_RUN) npm run package:binary')
    expect(targetChunk(source, 'smoke-linux-binary')).toContain(
      '$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME)',
    )
    expect(source.match(/\$\(NODE_RUN\) npm ci/g)).toHaveLength(1)
    expect(targetChunk(source, 'deps')).toContain('build/deps/node_modules.tar')
    expect(source).not.toContain('tee build/logs/publish-npm.log')
    expect(source).not.toContain('tee build/logs/npm-package.log')
    expect(source).not.toContain('tee build/logs/prune-package-versions.log')
    expect(targetChunk(source, '_docs')).toContain('node scripts/render-docs.mjs')
    const matchCi = [...source.matchAll(/^([a-z0-9-]+):.*?## Match CI/gm)].map((match) => match[1])
    expect(matchCi).toEqual(['setup', 'build', 'test', 'docs', 'login', 'publish-container'])
    expect(sdlc.toString('utf8')).toContain('tee build/logs/$(1).log')
  })

  it('builds the CI image once, smokes it, and publishes the lines from publish-tags', () => {
    expect(source).toContain('smoke-image: image')
    expect(source).not.toMatch(/^ci-image:/m)
    const image = targetChunk(source, 'image')
    expect(image).toContain('podman build')
    expect(image).toContain('-t "$(CI_IMAGE)"')
    expect(image).toContain('-t "$(IMAGE)"')
    expect(image).not.toMatch(/\bpush\b/)
    expect(targetChunk(source, 'smoke-image')).toContain('id="root"')
    expect(targetChunk(source, 'smoke-image')).toContain('podman run')
    expect(targetChunk(source, 'smoke-image')).not.toContain('podman build')
    const publish = targetChunk(source, '_publish-container')
    expect(publish).toContain('podman load -i build/image/$(NAME)-image.tar')
    expect(publish).toContain('$(THIS_MAKE) -s --no-print-directory version')
    expect(publish).toContain('build/publish-version.txt')
    expect(publish).toContain('podman push "$(IMAGE):$$tag"')
    expect(publish).toContain('$(THIS_MAKE) -s --no-print-directory publish-tags')
    expect(publish).toContain('for tag in $$tags')
    expect(publish).not.toContain('for tag in "$$version" latest')
    expect(publish).not.toContain('podman build')
    expect(publish).not.toContain('sha-')
    expect(publish).not.toMatch(/\bedge\b/)
    expect(publish).not.toContain('container-tags.mjs')
    expect(publish).not.toMatch(/\$\(MAKE\)/)
    expect(publish.indexOf('build/publish-version.txt')).toBeLessThan(publish.indexOf('podman push'))
    const login = targetChunk(source, 'login')
    expect(login).toContain('podman login ghcr.io --username')
    expect(login).toContain('--password-stdin')
    expect(login).toContain('REGISTRY_USER')
    expect(login).toContain('REGISTRY_TOKEN')
    expect(login).toContain('Match CI')
    expect(login).not.toMatch(/\$\(MAKE\)/)
  })

  it('keeps release commands that can run locally, and gates publish', () => {
    expect(source).not.toMatch(/^macos-package:/m)
    expect(source).not.toMatch(/^macos-binary:/m)
    expect(source).not.toMatch(/^publish-github:/m)
    expect(source).not.toMatch(/^release-assets:/m)
    expect(source).not.toMatch(/^npm-package:/m)
    expect(source).not.toMatch(/^publish-npm:/m)
    expect(source).not.toContain('scripts/release-notes.mjs')
    expect(source).not.toContain('SHA256SUMS')
    expect(source).not.toContain('gh release')
    expect(source).not.toContain('dashboard-macos')
    expect(source).not.toContain('NPM_PUBLISH')
    expect(source).not.toContain('npm publish')
    const container = targetChunk(source, '_publish-container')
    expect(container).toContain('build/summaries/publish-container.md')
    expect(container).toContain('Status: pushed')
    expect(container).not.toContain('gh release')
    expect(container).not.toContain('sha-')
    expect(container).not.toMatch(/\bedge\b/)
  })
})

describe('pipeline docs', () => {
  const rules = readFileSync(new URL('../docs/pipeline-rules.md', import.meta.url), 'utf8')
  const agents = readFileSync(new URL('../AGENTS.md', import.meta.url), 'utf8')

  it('records the version tag and that cleanup keeps the current version and one former', () => {
    for (const text of [rules, agents]) {
      expect(text).toContain('cleanup-container-versions')
      expect(text).not.toContain('prune-package-versions')
      expect(text).toContain('exactly one former')
      expect(text).toContain('next-lower')
      expect(text).toContain('tags the version only')
      expect(text).toContain('empty list')
      expect(text).toContain('MAJOR.MINOR.PATCH-<run>')
      expect(text).toContain('GitHub run number')
      expect(text).toContain('nearest v* tag')
      expect(text).toContain('does not invent a version')
      expect(text).toContain('A skipped or failed publish deletes nothing.')
      expect(text).toContain('latest')
    }
  })
})

describe('package and image contents', () => {
  const root = fileURLToPath(new URL('../', import.meta.url))
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))
  const npmignore = readFileSync(new URL('../.npmignore', import.meta.url), 'utf8')
  const containerignore = readFileSync(new URL('../.containerignore', import.meta.url), 'utf8')
  const containerfile = readFileSync(new URL('../Containerfile', import.meta.url), 'utf8')
  const keptOut = ['.claude/', 'AGENTS.md', 'CLAUDE.md', 'docs/', '.github/', 'data/dashboard.md', 'data/tls']

  it('keeps instruction and private files out of the tarball and the image', () => {
    for (const entry of keptOut) {
      expect(npmignore, entry).toContain(entry.replace(/\/$/, ''))
      expect(containerignore, entry).toContain(entry.replace(/\/$/, ''))
    }
    expect(pkg.files).toEqual([
      'server/bin/dashboard.mjs',
      'server/cli.mjs',
      'server/server.mjs',
      'server/dashboard-api.mjs',
      'server/tls-cert.mjs',
      'shared/openapi.json',
      'shared/validate.mjs',
      'dist',
      'data/dashboard.example.md',
    ])
    expect(containerfile).not.toMatch(/AGENTS\.md|\.claude|^COPY docs|docs\//m)
    expect(containerignore).toContain('*.tar')
    const gitignore = readFileSync(new URL('../.gitignore', import.meta.url), 'utf8')
    for (const line of ['ci-artifacts', 'release', '*.local', '*-image.tar']) {
      expect(gitignore, line).toContain(line)
    }
  })

  it('packs only the built app', () => {
    const raw = execFileSync('npm', ['pack', '--dry-run', '--ignore-scripts', '--json'], {
      cwd: root,
      encoding: 'utf8',
    })
    const packed = JSON.parse(raw)
    const paths = packed[0].files.map((file) => file.path)
    const allowed = new Set(pkg.files.filter((entry) => entry !== 'dist'))
    for (const file of paths) {
      const built = file.startsWith('dist/') || file === 'dist'
      const listed = allowed.has(file) || file === 'package.json' || file === 'README.md'
      expect(built || listed, file).toBe(true)
      expect(file.startsWith('docs/'), file).toBe(false)
      expect(file.startsWith('.claude/'), file).toBe(false)
      expect(file).not.toBe('AGENTS.md')
      expect(file.startsWith('src/'), file).toBe(false)
      expect(file.endsWith('.test.mjs'), file).toBe(false)
    }
    expect(paths).toContain('server/bin/dashboard.mjs')
  })
})
