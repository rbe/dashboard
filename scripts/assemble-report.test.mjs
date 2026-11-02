import { mkdirSync, mkdtempSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { assemble, explainContainer, explainNpm } from './assemble-report.mjs'

const sha = '0123456789abcdef0123456789abcdef01234567'

function write(root, rel, text) {
  const dest = path.join(root, rel)
  mkdirSync(path.dirname(dest), { recursive: true })
  writeFileSync(dest, text)
}

function workspace() {
  const root = mkdtempSync(path.join(tmpdir(), 'dashboard-report-'))
  write(root, 'package.json', '{ "version": "1.0.0" }\n')
  return root
}

describe('publish explanations', () => {
  it('explains a branch push that skips the image', () => {
    expect(
      explainContainer({
        event: 'push',
        ref: 'refs/heads/feature/pipeline',
        result: 'skipped',
      }),
    ).toContain('This branch stops before publish')
  })

  it('explains a master push that skips npm when the variable is off', () => {
    expect(
      explainNpm({
        event: 'push',
        ref: 'refs/heads/master',
        result: 'skipped',
        npmPublish: '',
      }),
    ).toContain('NPM_PUBLISH is not true')
  })

  it('explains a manual container publish whose producers failed', () => {
    expect(
      explainContainer({
        event: 'workflow_dispatch',
        ref: 'refs/heads/feature/pipeline',
        dispatchJob: 'publish-container',
        result: 'skipped',
      }),
    ).toContain('setup, build, or test did not succeed')
  })

  it('keeps the recorded tags when the image was pushed', () => {
    const summary = '# publish-container\n\nStatus: pushed\nTags:\n- ghcr.io/rbe/dashboard:edge\n'
    expect(
      explainContainer({
        event: 'push',
        ref: 'refs/heads/master',
        result: 'success',
        summary,
      }),
    ).toContain('ghcr.io/rbe/dashboard:edge')
  })
})

describe('assemble report', () => {
  it('collects tests, coverage, logs, and a skipped publish into one report', () => {
    const root = workspace()
    try {
      write(
        root,
        'build/inputs/report-test/test-results.json',
        JSON.stringify({
          numTotalTests: 2,
          numPassedTests: 1,
          numFailedTests: 1,
          numPendingTests: 0,
          success: false,
          startTime: 1_000,
          testResults: [
            {
              endTime: 1_500,
              assertionResults: [
                { fullName: 'board renders', status: 'passed' },
                {
                  fullName: 'board saves',
                  status: 'failed',
                  failureMessages: ['expected saved\nreceived missing'],
                },
              ],
            },
          ],
        }),
      )
      write(
        root,
        'build/inputs/report-test/coverage/coverage-summary.json',
        JSON.stringify({
          total: {
            lines: { pct: 80 },
            statements: { pct: 75 },
            functions: { pct: 70 },
            branches: { pct: 60 },
          },
        }),
      )
      write(root, 'build/inputs/report-test/coverage/lcov.info', 'TN:\n')
      write(root, 'build/inputs/report-test/logs/test.log', 'npm test\nFAIL board saves\n')
      write(root, 'build/inputs/report-setup/logs/setup.log', 'npm audit reported advisories; continuing\n')
      write(root, 'build/inputs/report-setup/summaries/setup.md', '# setup\n\nnode_modules archive: ci-artifacts/node_modules.tar\n')
      write(
        root,
        'build/inputs/report-build/summaries/build.md',
        '# build\n\nLinux binary: build/dashboard\nImage archive: dashboard-image.tar (10 bytes)\n',
      )
      write(root, 'build/inputs/report-build/logs/build.log', 'Wrote build/dashboard\n')
      write(root, 'build/inputs/report-npm-package/summaries/npm-package.md', '# npm-package\n\nTarball: build/dashboard-1.0.0.tgz\n')
      write(root, 'build/inputs/report-docs/summaries/docs.md', '# docs\n\n- pipeline-rules.md\n')
      write(root, 'build/inputs/report-npm-package/dashboard-1.0.0.tgz', 'not a release asset')
      write(root, 'build/inputs/report-build/dashboard-image.tar', 'not a release asset')

      const markdown = assemble({
        root,
        env: {
          GITHUB_EVENT_NAME: 'push',
          GITHUB_REF: 'refs/heads/feature/pipeline',
          GITHUB_REF_NAME: 'feature/pipeline',
          GITHUB_SHA: sha,
          GITHUB_REPOSITORY: 'rbe/dashboard',
          NODE_VERSION: '24',
          IMAGE_NAME: 'ghcr.io/rbe/dashboard',
          NPM_PUBLISH: '',
          JOB_RESULT_SETUP: 'success',
          JOB_RESULT_BUILD: 'success',
          JOB_RESULT_TEST: 'failure',
          JOB_RESULT_NPM_PACKAGE: 'success',
          JOB_RESULT_DOCS: 'success',
          JOB_RESULT_PUBLISH_NPM: 'skipped',
          JOB_RESULT_PUBLISH_IMAGE: 'skipped',
        },
      })

      expect(markdown).toContain('Tests: 1 failed, 1 passed.')
      expect(markdown).toContain('board saves')
      expect(markdown).toContain('expected saved')
      expect(markdown).toContain('Coverage lines: 80%.')
      expect(markdown).toContain('| branches | 60 |')
      expect(markdown).toContain('This branch stops before publish')
      expect(markdown).toContain('The npm package was not published.')
      expect(markdown).toContain('GitHub release: none')
      expect(markdown).toContain('npm audit reported advisories')
      expect(markdown).toContain('Linux binary: build/dashboard')
      expect(markdown).toContain('Tarball: build/dashboard-1.0.0.tgz')
      expect(markdown).toContain('pipeline-rules.md')
      expect(markdown).toContain(`| Commit | ${sha} |`)
      expect(markdown).toContain('| publish-container | skipped |')
      expect(markdown).toContain('logs/')

      const index = readFileSync(path.join(root, 'build/report/index.md'), 'utf8')
      expect(index).toBe(markdown)
      expect(readFileSync(path.join(root, 'build/report/test-results.json'), 'utf8')).toContain('board saves')
      expect(readFileSync(path.join(root, 'build/report/coverage/coverage-summary.json'), 'utf8')).toContain('"pct":80')
      expect(readFileSync(path.join(root, 'build/report/coverage/lcov.info'), 'utf8')).toContain('TN:')
      const copied = readFileSync(path.join(root, 'build/report/index.md'), 'utf8')
      expect(copied).not.toContain('not a release asset')
      expect(exists(path.join(root, 'build/report'), '.tgz')).toBe(false)
      expect(exists(path.join(root, 'build/report'), '.tar')).toBe(false)
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('records pushed tags and a manual npm skip', () => {
    const root = workspace()
    try {
      write(
        root,
        'build/summaries/publish-container.md',
        '# publish-container\n\nStatus: pushed\nImage: ghcr.io/rbe/dashboard\nTags:\n- ghcr.io/rbe/dashboard:sha-0123456789ab\nReason: A manual publish-container publishes sha-<commit> from this ref.\n',
      )
      const markdown = assemble({
        root,
        env: {
          GITHUB_EVENT_NAME: 'workflow_dispatch',
          GITHUB_REF: 'refs/heads/feature/pipeline',
          GITHUB_REF_NAME: 'feature/pipeline',
          GITHUB_SHA: sha,
          DISPATCH_JOB: 'publish-container',
          IMAGE_NAME: 'ghcr.io/rbe/dashboard',
          NODE_VERSION: '24',
          JOB_RESULT_PUBLISH_IMAGE: 'success',
          JOB_RESULT_PUBLISH_NPM: 'skipped',
        },
      })
      expect(markdown).toContain('Image pushed: ghcr.io/rbe/dashboard:sha-0123456789ab.')
      expect(markdown).toContain('sha-<commit>')
      expect(markdown).toContain('Run workflow selected `publish-container`, so the npm package was not published.')
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })
})

function exists(dir, extension) {
  const pending = [dir]
  while (pending.length > 0) {
    const current = pending.pop()
    for (const name of readdirSync(current)) {
      const full = path.join(current, name)
      if (statSync(full).isDirectory()) pending.push(full)
      else if (name.endsWith(extension)) return true
    }
  }
  return false
}
