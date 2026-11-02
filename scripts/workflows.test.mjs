import { execFileSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

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
  return [...chunk.matchAll(/^\s*run: make (\S+)\s*$/gm)].map((match) => match[1])
}

describe('workflow', () => {
  const source = read('ci.yml')
  const pipeline = jobs(source)
  const pkg = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8'))

  it('is the only workflow and does not call another workflow', () => {
    expect(files()).toEqual(['ci.yml'])
    const on = triggers(source)
    expect(on.workflow_call).toBe(false)
    expect(on.workflow_dispatch).toBe(true)
    expect(on.pull_request).toBe(false)
    expect(on.everyBranch).toBe(true)
    expect(on.masterOnly).toBe(false)
    expect(on.tags).toBe(true)
    expect(source).not.toMatch(/uses:\s*\.\/\.github\/workflows\//)
    expect(source).not.toMatch(/\bhost-checks\b|\bci-image\b|\bnpm-tarball\b|\bmacos-binary\b|\bmacos-package\b|\bnpm-publish\b|\bpublish-github\b|\bnpm-package\b|\bpublish-npm\b/)
    expect(source).not.toMatch(/\bNPM_PUBLISH\b|\bNPM_TOKEN\b|\bid-token\b/)
    expect(source).not.toContain('actions/setup-node')
    expect(source).not.toContain('macos-latest')
    expect(source).not.toContain('dashboard-macos')
    expect(source).not.toMatch(/\bgh release\b|action-gh-release|upload-release-asset|softprops/)
    expect(source).not.toContain('SHA256SUMS')
    expect(source).not.toMatch(/contents:\s*write/)
    expect(source).not.toMatch(/docker/i)
    expect(source).not.toMatch(/\bnpm ci\b|\bnpm test\b|\bnpm pack\b|\bnpm publish\b/)
    expect(source).not.toMatch(/\bernaehrung\b/)
  })

  it('names the jobs in pipeline order and runs that make target once', () => {
    expect(Object.keys(pipeline)).toEqual(jobNames)
    const options = [...source.matchAll(/^\s+- ([a-z0-9-]+)\s*$/gm)].map((match) => match[1])
    expect(options).toEqual(jobNames)
    for (const name of jobNames) {
      expect(makeCalls(pipeline[name]), name).toEqual([name])
    }
  })

  it('keeps the image name and the package version in one place', () => {
    expect(source.match(/ghcr\.io\/rbe\/dashboard/g)).toEqual(['ghcr.io/rbe/dashboard'])
    expect(source.match(/^ {2}IMAGE_NAME:/gm)).toHaveLength(1)
    expect(source.match(/^ {2}VERSION:.*$/gm)).toEqual([`  VERSION: "${pkg.version}"`])
    expect(source).toContain('NODE_VERSION: "24"')
    expect(source).toContain('actions/checkout@v7')
    expect(source).toContain('actions/upload-artifact@v7')
    expect(source).toContain('actions/download-artifact@v8')
    expect(source).not.toMatch(/actions\/(checkout|upload-artifact|setup-node)@v[0-6]\b/)
    expect(source).not.toMatch(/actions\/download-artifact@v[0-7]\b/)
  })

  it('passes artifacts forward and does not rebuild them in a later job', () => {
    expect(pipeline.setup).toContain('name: node_modules')
    expect(pipeline.setup).toContain('path: ci-artifacts/node_modules.tar')
    expect(pipeline.build).toContain('name: node_modules')
    expect(pipeline.build).toContain('name: dist')
    expect(pipeline.build).toContain('name: container-image')
    expect(pipeline.build).toContain('${{ github.event.repository.name }}-image.tar')
    expect(pipeline.build).not.toContain('make setup')
    expect(pipeline.test).toContain('name: node_modules')
    expect(pipeline.test).toContain('name: report-test')
    expect(pipeline.test).toContain('build/test-results.json')
    expect(pipeline.test).toContain('build/coverage')
    expect(pipeline.test).toContain('build/logs')
    expect(pipeline.test).not.toContain('needs.test.outputs.reports')
    expect(pipeline.report).toContain('needs: [setup, build, test, docs, publish-container]')
    expect(pipeline.report).toContain('always() && !cancelled()')
    expect(pipeline.report).toContain('pattern: report-*')
    expect(pipeline.report).toContain('path: build/inputs')
    expect(pipeline.report).toContain('name: report')
    expect(pipeline.report).toContain('path: build/report')
    expect(pipeline.report).not.toContain('macos-package')
    expect(pipeline.report).not.toContain("needs.publish-container.result == 'success'")
    expect(pipeline.report).not.toContain("needs.publish-container.result == 'failure'")
    expect(pipeline.report).not.toContain("needs.publish-container.result == 'skipped'")
    expect(pipeline.report).not.toContain('gh release')
    expect(pipeline['publish-container']).toContain('name: container-image')
    expect(pipeline['publish-container']).not.toMatch(/make (build|image|ci-image|setup)\b/)
    expect(pipeline['publish-container']).not.toContain('podman build')
    expect(pipeline['publish-container']).toContain('name: report-publish-container')
    expect(pipeline['publish-container']).not.toContain('gh release')
    expect(pipeline['publish-container']).not.toContain('name: docs')
    expect(pipeline.docs).toContain('needs: setup')
    expect(pipeline.docs).toContain('name: docs')
    expect(pipeline.docs).toContain('path: build/docs')
    expect(pipeline.docs).toContain('if-no-files-found: ignore')
    expect(pipeline.docs).not.toContain('needs: build')
    expect(pipeline.docs).not.toContain('needs: test')
    expect(pipeline.docs).not.toContain('needs: [')
  })

  it('publishes the image from master or main, or from a manual run of that job', () => {
    expect(pipeline['publish-container']).toContain("inputs.job == 'publish-container'")
    expect(pipeline['publish-container']).toContain("github.event_name == 'workflow_dispatch'")
    expect(pipeline['publish-container']).toContain("github.event_name == 'push'")
    expect(pipeline['publish-container']).toContain("github.ref == 'refs/heads/master'")
    expect(pipeline['publish-container']).toContain("github.ref == 'refs/heads/main'")
    expect(pipeline['publish-container']).not.toContain('refs/tags')
    expect(pipeline['publish-container']).not.toContain('refs/heads/**')
    expect(pipeline['publish-container']).toContain("needs.test.result == 'success'")
    expect(pipeline['publish-container']).toContain("needs.build.result == 'success'")
    expect(pipeline['publish-container']).toContain('needs: [build, test]')
    expect(pipeline['publish-container']).not.toContain('needs: [build, test, report]')
    expect(pipeline['publish-container']).not.toContain('docs')
    expect(pipeline['publish-container']).toContain('packages: write')
    expect(pipeline['publish-container']).toContain('podman login')
    expect(pipeline['publish-container']).toContain('--password-stdin')
    expect(pipeline['publish-container']).toContain('${IMAGE_NAME%%/*}')
    expect(pipeline['publish-container']).not.toContain('dashboard-macos')
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
    expect(pipeline.test).toContain("inputs.job == 'publish-container'")
    expect(pipeline.build).toContain("inputs.job == 'publish-container'")
    expect(pipeline.setup).toContain("inputs.job == 'publish-container'")
    expect(pipeline.docs).not.toContain("inputs.job == 'publish-container'")
    expect(pipeline.setup).toContain("inputs.job == 'report'")
    expect(pipeline.build).toContain("inputs.job == 'report'")
    expect(pipeline.test).toContain("inputs.job == 'report'")
    expect(pipeline.docs).toContain("inputs.job == 'report'")
    expect(pipeline['publish-container']).not.toContain("inputs.job == 'report'")
    expect(pipeline.report).toContain('needs: [setup, build, test, docs, publish-container]')
    expect(pipeline.report).toContain('always() && !cancelled()')
    for (const name of ['setup', 'build', 'test', 'docs', 'publish-container']) {
      expect(pipeline[name], name).toContain(`name: report-${name}`)
      expect(pipeline[name], name).toContain('build/logs')
    }
    for (const name of jobNames) {
      expect(pipeline[name], name).toContain('runs-on: ubuntu-26.04')
    }
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
    expect(targetChunk(source, 'image')).toContain('podman build')
    expect(targetChunk(source, 'image')).not.toContain('npm')
    expect(targetChunk(source, 'run')).toContain('podman run')
    expect(targetChunk(source, 'run')).not.toContain('npm')
    expect(source).toContain('ci: setup build test docs report')
    expect(source).not.toMatch(/^npm-package:/m)
    expect(source).not.toMatch(/^publish-npm:/m)
    expect(source).not.toMatch(/^publish-github:/m)
    expect(source).not.toContain('ci: host-checks')
  })

  it('splits the old host checks across the job targets', () => {
    expect(source).toContain('setup: check-tag npm-ci audit')
    expect(targetChunk(source, 'audit')).toContain('npm audit --audit-level=high || echo "npm audit reported advisories; continuing"')
    expect(targetChunk(source, 'check-tag')).toContain('refs/tags/v')
    expect(targetChunk(source, 'npm-ci')).toContain('$(NODE_RUN) npm ci')
    expect(targetChunk(source, 'test')).toContain('npm test -- --coverage')
    expect(targetChunk(source, 'test')).toContain('build/test-results.json')
    expect(targetChunk(source, 'build')).toContain('linux-binary')
    expect(targetChunk(source, 'build')).toContain('smoke-image')
    expect(targetChunk(source, 'build')).toContain('image-save')
    expect(targetChunk(source, 'build')).not.toContain('npm ci')
    expect(targetChunk(source, 'linux-binary')).toContain('$(NODE_RUN) npm run package:binary')
    expect(targetChunk(source, 'smoke-linux-binary')).toContain(
      '$(NODE_RUN) node scripts/smoke-binary.mjs build/$(NAME)',
    )
    expect(source.match(/\$\(NODE_RUN\) npm ci/g)).toHaveLength(1)
    expect(targetChunk(source, 'deps')).toContain('ci-artifacts/node_modules.tar')
    expect(targetChunk(source, 'report')).toContain('node scripts/assemble-report.mjs')
    expect(targetChunk(source, 'report')).not.toContain('Skipping.')
    expect(source).toContain('tee build/logs/setup.log')
    expect(source).toContain('tee build/logs/build.log')
    expect(source).toContain('tee build/logs/test.log')
    expect(source).toContain('tee build/logs/docs.log')
    expect(source).toContain('tee build/logs/publish-container.log')
    expect(source).not.toContain('tee build/logs/publish-npm.log')
    expect(source).not.toContain('tee build/logs/npm-package.log')
    expect(targetChunk(source, 'docs')).toContain('node scripts/render-docs.mjs')
    const matchCi = [...source.matchAll(/^([a-z0-9-]+):.*?## Match CI/gm)].map((match) => match[1])
    expect(matchCi).toEqual(['setup', 'build', 'test', 'docs', 'publish-container', 'report'])
  })

  it('builds the CI image once and smokes that image', () => {
    expect(source).toContain('ci-image: smoke-image')
    expect(source).toContain('smoke-image: image')
    const image = targetChunk(source, 'image')
    expect(image).toContain('podman build')
    expect(image).toContain('-t "$(CI_IMAGE)"')
    expect(image).toContain('-t "$(IMAGE)"')
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
    const publish = targetChunk(source, 'publish-container')
    expect(publish).toContain('image-load')
    expect(publish).toContain('resolve-ghcr-tags')
    expect(publish).toContain('image-push')
    expect(publish).not.toContain('podman build')
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
    const container = targetChunk(source, 'publish-container')
    expect(container).toContain('build/summaries/publish-container.md')
    expect(container).toContain('Status:')
    expect(container).not.toContain('gh release')
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
      'bin/dashboard.mjs',
      'scripts/cli.mjs',
      'scripts/server.mjs',
      'scripts/dashboard-api.mjs',
      'scripts/tls-cert.mjs',
      'dist',
      'data/dashboard.example.md',
    ])
    expect(containerfile).not.toMatch(/AGENTS\.md|\.claude|^COPY docs|docs\//m)
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
    expect(paths).toContain('bin/dashboard.mjs')
  })
})
