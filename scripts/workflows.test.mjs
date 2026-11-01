import { execFileSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const workflowDir = new URL('../.github/workflows/', import.meta.url)
const jobNames = [
  'setup',
  'build',
  'test',
  'npm-package',
  'report',
  'docs',
  'publish-npm',
  'publish-container',
  'publish-github',
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
    expect(source).not.toMatch(/\bhost-checks\b|\bci-image\b|\bnpm-tarball\b|\bmacos-binary\b|\bmacos-package\b|\bnpm-publish\b/)
    expect(source).not.toContain('macos-latest')
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
    expect(source).toContain('actions/setup-node@v7')
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
    expect(pipeline.test).toContain('name: test-reports')
    expect(pipeline.test).toContain('build/test-results.json')
    expect(pipeline.test).toContain('build/coverage')
    expect(pipeline.test).not.toContain('needs.test.outputs.reports')
    expect(pipeline.test).toContain('reports: ${{ steps.reports.outputs.reports }}')
    expect(pipeline['npm-package']).toContain('needs: [build, test]')
    expect(pipeline['npm-package']).toContain("needs.build.result == 'success'")
    expect(pipeline['npm-package']).toContain("needs.test.result == 'success'")
    expect(pipeline['npm-package']).toContain('name: node_modules')
    expect(pipeline['npm-package']).toContain('name: dist')
    expect(pipeline['npm-package']).toContain('name: npm-package')
    expect(pipeline['npm-package']).not.toContain('make build')
    expect(pipeline['npm-package']).not.toContain('continue-on-error')
    expect(pipeline.report).toContain('needs: test')
    expect(pipeline.report).not.toContain('macos-package')
    expect(pipeline.report).toContain('name: test-reports')
    expect(pipeline.report).toContain("needs.test.outputs.reports == 'true'")
    expect(pipeline['publish-npm']).toContain('name: npm-package')
    expect(pipeline['publish-npm']).not.toContain('make npm-package')
    expect(pipeline['publish-container']).toContain('name: container-image')
    expect(pipeline['publish-container']).not.toMatch(/make (build|image|ci-image|setup)\b/)
    expect(pipeline['publish-container']).not.toContain('podman build')
    expect(pipeline['publish-github']).toContain('needs: [npm-package, test, report]')
    expect(pipeline['publish-github']).toContain('name: npm-package')
    expect(pipeline['publish-github']).toContain("needs.npm-package.result == 'success'")
    expect(pipeline['publish-github']).not.toContain('make npm-package')
    expect(pipeline['publish-github']).not.toContain('publish-npm')
    expect(pipeline['publish-github']).not.toContain('publish-container')
    expect(pipeline['publish-github']).not.toContain('name: docs')
    expect(pipeline.docs).toContain('name: docs')
    expect(pipeline.docs).toContain('path: build/docs')
    expect(pipeline.docs).toContain('if-no-files-found: ignore')
    expect(pipeline.docs).not.toContain('needs:')
    expect(pipeline['npm-package']).not.toContain('name: docs')
    expect(pipeline['publish-container']).not.toContain('name: docs')
  })

  it('publishes on the default branch, a version tag, or a manual run of that job', () => {
    for (const name of ['publish-npm', 'publish-container', 'publish-github']) {
      expect(pipeline[name], name).toContain("inputs.job == '" + name + "'")
      expect(pipeline[name], name).toContain("github.event_name == 'workflow_dispatch'")
      expect(pipeline[name], name).toContain("github.ref == 'refs/heads/master'")
      expect(pipeline[name], name).toContain("github.ref == 'refs/heads/main'")
      expect(pipeline[name], name).toContain("startsWith(github.ref, 'refs/tags/v')")
      expect(pipeline[name], name).not.toContain('refs/heads/**')
    }
    expect(pipeline['publish-npm']).toContain("vars.NPM_PUBLISH == 'true'")
    expect(pipeline['publish-npm']).toContain("github.event_name == 'workflow_dispatch' && 'true' || vars.NPM_PUBLISH")
    expect(pipeline['publish-npm']).toContain('id-token: write')
    expect(pipeline['publish-npm']).toContain('registry-url: https://registry.npmjs.org')
    expect(pipeline['publish-container']).toContain("needs.test.result == 'success'")
    expect(pipeline['publish-container']).toContain('packages: write')
    expect(pipeline['publish-container']).toContain('podman login')
    expect(pipeline['publish-container']).toContain('--password-stdin')
    expect(pipeline['publish-container']).toContain('${IMAGE_NAME%%/*}')
    expect(pipeline['publish-github']).toContain('contents: write')
    expect(pipeline['publish-github']).toContain('gh release create')
    expect(pipeline['publish-github']).toContain('gh release upload')
    expect(pipeline['publish-github']).toContain('build/notes.md')
    expect(pipeline['publish-github']).toContain('build/SHA256SUMS')
    expect(pipeline['publish-github']).not.toContain('dashboard-macos')
    expect(source.match(/packages: write/g)).toHaveLength(1)
    expect(source.match(/id-token: write/g)).toHaveLength(1)
    expect(source.match(/contents: write/g)).toHaveLength(1)
  })

  it('runs build beside test, and a manual publish-github runs the pack', () => {
    expect(pipeline.build).toContain('needs: setup')
    expect(pipeline.test).toContain('needs: setup')
    expect(pipeline.test).not.toContain('needs: build')
    expect(pipeline.test).toContain("inputs.job == 'publish-github'")
    expect(pipeline.build).toContain("inputs.job == 'publish-github'")
    expect(pipeline.setup).toContain("inputs.job == 'publish-github'")
    expect(pipeline['npm-package']).toContain("inputs.job == 'publish-github'")
    expect(pipeline.test).toContain("inputs.job == 'publish-container'")
    expect(pipeline.build).toContain("inputs.job == 'publish-container'")
    expect(pipeline.setup).toContain("inputs.job == 'publish-container'")
    expect(pipeline['npm-package']).not.toContain("inputs.job == 'publish-container'")
    expect(pipeline['publish-container']).toContain("needs.build.result == 'success'")
    expect(pipeline['publish-npm']).toContain('needs: [npm-package, test, report]')
    expect(pipeline['publish-container']).toContain('needs: [build, test, report]')
    expect(pipeline['publish-npm']).not.toContain('publish-container')
    expect(pipeline['publish-container']).not.toContain('publish-github')
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
    expect(source).toContain('ci: setup build test npm-package report docs')
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
    const pack = targetChunk(source, 'npm-package')
    expect(pack).toContain('npm pack --ignore-scripts --pack-destination build')
    expect(pack).toContain('npm install -g "./$$tgz"')
    expect(pack).toContain('grep -qx package/dist/index.html')
    expect(pack).not.toContain('npm run build')
    expect(pack).toContain('node scripts/smoke-binary.mjs')
    expect(source.match(/\$\(NODE_RUN\) npm ci/g)).toHaveLength(1)
    expect(targetChunk(source, 'deps')).toContain('ci-artifacts/node_modules.tar')
    expect(targetChunk(source, 'report')).toContain('No coverage report or test output. Skipping.')
    expect(targetChunk(source, 'docs')).toContain('node scripts/render-docs.mjs')
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
    const tarball = targetChunk(source, 'npm-package')
    expect(tarball).toContain('npm pack --ignore-scripts --pack-destination build')
    expect(tarball).not.toContain('npm run build')
    const notes = targetChunk(source, 'publish-github')
    expect(notes).toContain('node scripts/release-notes.mjs')
    expect(notes).toContain('SHA256SUMS')
    expect(notes).toContain('It does not pack again.')
    expect(notes).not.toContain('npm pack')
    expect(notes).not.toContain('macos-package')
    const publish = targetChunk(source, 'publish-npm')
    expect(publish).toContain('NPM_PUBLISH')
    expect(publish).toContain('npm publish "./$$tgz" --access public --provenance')
    expect(publish).not.toContain('npm ci')
    expect(publish).not.toContain('$(MAKE) npm-package')
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
