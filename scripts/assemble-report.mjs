import { cpSync, existsSync, mkdirSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const JOBS = [
  ['setup', 'JOB_RESULT_SETUP'],
  ['build', 'JOB_RESULT_BUILD'],
  ['test', 'JOB_RESULT_TEST'],
  ['docs', 'JOB_RESULT_DOCS'],
  ['publish-container', 'JOB_RESULT_PUBLISH_IMAGE'],
]

export function isPublishRef(ref) {
  return ref === 'refs/heads/master' || ref === 'refs/heads/main'
}

export function explainContainer({ event = '', ref = '', dispatchJob = '', result = '', summary = '' }) {
  if (result === 'success' || result === 'ran' || result === 'failure') {
    if (summary) return summary.trim()
    if (result === 'failure') return 'publish-container failed before it recorded tags. See the log.'
    if (result === 'success') return 'publish-container succeeded but did not record tags.'
    return 'No container publish summary was recorded.'
  }
  if (!event && !ref && !dispatchJob) {
    return 'No container publish was recorded. A local report does not push the image.'
  }
  if (event === 'workflow_dispatch' && dispatchJob && dispatchJob !== 'publish-container') {
    return `Run workflow selected \`${dispatchJob}\`, so the image was not pushed.`
  }
  if (event === 'workflow_dispatch' && dispatchJob === 'publish-container') {
    return 'publish-container was skipped because setup, build, or test did not succeed.'
  }
  if (event === 'push' && String(ref || '').startsWith('refs/tags/')) {
    return 'A tag push does not publish the image. publish-container runs on a push to `master` or `main`, and when Run workflow selects it.'
  }
  if (event === 'push' && !isPublishRef(ref)) {
    return 'This branch stops before publish. A push publishes the image only from `master` or `main`.'
  }
  if (event === 'push' && isPublishRef(ref)) {
    return 'publish-container was skipped because build or test did not succeed.'
  }
  if (result === 'cancelled') return 'publish-container was cancelled.'
  return 'publish-container did not run.'
}

function walk(dir, acc = []) {
  if (!existsSync(dir)) return acc
  for (const name of readdirSync(dir)) {
    const full = path.join(dir, name)
    let info
    try {
      info = statSync(full)
    } catch {
      continue
    }
    if (info.isDirectory()) walk(full, acc)
    else acc.push(full)
  }
  return acc
}

function readText(file) {
  return readFileSync(file, 'utf8')
}

function readJson(file) {
  try {
    return JSON.parse(readFileSync(file, 'utf8'))
  } catch {
    return null
  }
}

function packageVersion(root) {
  try {
    return JSON.parse(readFileSync(path.join(root, 'package.json'), 'utf8')).version || ''
  } catch {
    return ''
  }
}

function flattenName(root, file) {
  return path.relative(root, file).split(path.sep).join('__')
}

function pickTestResults(files) {
  const matches = files.filter((file) => path.basename(file) === 'test-results.json')
  matches.sort((a, b) => {
    const aScore = a.includes(`${path.sep}report-test${path.sep}`) ? 0 : 1
    const bScore = b.includes(`${path.sep}report-test${path.sep}`) ? 0 : 1
    return aScore - bScore || a.length - b.length
  })
  return matches[0] || ''
}

function pickCoverage(files) {
  const summaries = files.filter((file) => path.basename(file) === 'coverage-summary.json')
  if (summaries.length > 0) return path.dirname(summaries[0])
  const nested = files.find((file) => file.split(path.sep).includes('coverage'))
  return nested ? path.dirname(nested) : ''
}

function parseTests(json) {
  if (!json || typeof json !== 'object') return { present: false, total: 0, passed: 0, failed: 0, pending: 0, failures: [] }
  const failures = []
  for (const suite of json.testResults || []) {
    for (const test of suite.assertionResults || []) {
      if (test.status !== 'failed') continue
      const name = test.fullName || [...(test.ancestorTitles || []), test.title].filter(Boolean).join(' ')
      const message = Array.isArray(test.failureMessages) ? test.failureMessages[0] || '' : ''
      failures.push({ name: name || suite.name || 'failed test', message: message.slice(0, 400) })
    }
  }
  const start = Number(json.startTime)
  const end = Number(json.endTime || json.testResults?.[0]?.endTime)
  return {
    present: true,
    total: Number(json.numTotalTests ?? failures.length) || 0,
    passed: Number(json.numPassedTests ?? 0) || 0,
    failed: Number(json.numFailedTests ?? failures.length) || 0,
    pending: Number(json.numPendingTests ?? 0) || 0,
    durationMs: Number.isFinite(start) && Number.isFinite(end) && end >= start ? end - start : 0,
    success: json.success !== false && (Number(json.numFailedTests ?? failures.length) || 0) === 0,
    failures: failures.slice(0, 8),
  }
}

function pct(section) {
  if (!section || section.pct === undefined || section.pct === null) return ''
  return String(section.pct)
}

function parseCoverage(summary) {
  const total = summary?.total
  if (!total) return { present: false }
  return {
    present: true,
    lines: pct(total.lines),
    statements: pct(total.statements),
    functions: pct(total.functions),
    branches: pct(total.branches),
  }
}

function statusOf(summary) {
  const match = String(summary || '').match(/^Status:\s*(.+)$/m)
  return match ? match[1].trim() : ''
}

function tagsOf(summary) {
  const tags = []
  let reading = false
  for (const line of String(summary || '').split('\n')) {
    if (line.startsWith('Tags:')) {
      reading = true
      const rest = line.slice('Tags:'.length).trim()
      if (rest && rest !== 'none') tags.push(rest)
      continue
    }
    if (!reading) continue
    if (line.startsWith('- ')) tags.push(line.slice(2).trim())
    else if (line.trim() === '') reading = false
    else reading = false
  }
  return tags.filter((tag) => tag && tag !== 'none')
}

function auditExcerpt(text) {
  const lines = String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => /vulnerabilit|npm audit reported advisories/i.test(line))
  return lines.slice(-3).join('\n')
}

function jobEvidence(name, ctx) {
  if (name === 'publish-container') return Boolean(ctx.summaries.container)
  if (name === 'test') return ctx.tests.present || ctx.coverage.present
  if (ctx.summaries[name]) return true
  return ctx.logs.some((log) => log.name.includes(name))
}

function displayResult(value, evidence) {
  if (value) return value
  if (evidence) return 'ran'
  return 'not recorded'
}

export function loadReport(root, env = process.env) {
  const build = path.join(root, 'build')
  const files = [
    ...walk(path.join(build, 'inputs')),
    ...walk(path.join(build, 'logs')),
    ...walk(path.join(build, 'summaries')),
  ]
  const directResults = path.join(build, 'test-results.json')
  const directCoverage = path.join(build, 'coverage')
  if (existsSync(directResults)) files.push(directResults)
  if (existsSync(directCoverage)) files.push(...walk(directCoverage))

  const logs = []
  const summaries = { setup: '', build: '', docs: '', container: '' }
  for (const file of files) {
    if (file.endsWith('.tgz') || file.endsWith('.tar')) continue
    const base = path.basename(file)
    if (base.endsWith('.log')) {
      logs.push({ name: flattenName(path.join(build), file), file, text: readText(file) })
      continue
    }
    if (file.split(path.sep).includes('summaries') && base.endsWith('.md')) {
      const text = readText(file)
      if (base === 'publish-container.md') summaries.container = text
      else if (base === 'setup.md') summaries.setup = text
      else if (base === 'build.md') summaries.build = text
      else if (base === 'docs.md') summaries.docs = text
    }
  }

  const testFile = pickTestResults(files)
  const tests = parseTests(testFile ? readJson(testFile) : null)
  const coverageDir = pickCoverage(files)
  const coverage = parseCoverage(coverageDir ? readJson(path.join(coverageDir, 'coverage-summary.json')) : null)
  const setupLog = logs.find((log) => log.name.includes('setup'))
  const jobs = JOBS.map(([name, key]) => {
    const evidence = jobEvidence(name, { summaries, logs, tests, coverage })
    return { name, result: displayResult(env[key] || '', evidence) }
  })

  return {
    version: packageVersion(root),
    nodeVersion: env.NODE_VERSION || '',
    imageName: env.IMAGE_NAME || '',
    event: env.GITHUB_EVENT_NAME || '',
    ref: env.GITHUB_REF || '',
    refName: env.GITHUB_REF_NAME || '',
    sha: env.GITHUB_SHA || '',
    repository: env.GITHUB_REPOSITORY || '',
    dispatchJob: env.DISPATCH_JOB || '',
    jobs,
    logs,
    summaries,
    tests,
    coverage,
    audit: auditExcerpt(setupLog?.text || ''),
    testFile,
    coverageDir,
  }
}

function fence(text) {
  return String(text || '').trim()
}

function testLead(tests) {
  if (!tests.present) return 'Tests: no results were collected.'
  if (tests.failed > 0) return `Tests: ${tests.failed} failed, ${tests.passed} passed.`
  return `Tests: ${tests.passed} passed.`
}

function containerLead(summary, body) {
  const status = statusOf(summary)
  const tags = tagsOf(summary)
  if (status === 'pushed' && tags.length > 0) return `Image pushed: ${tags.join(', ')}.`
  if (status === 'pushed') return 'Image pushed.'
  if (status === 'failed' || status === 'refused') return `Image not pushed (${status}).`
  const sentence = body.split('\n').find((line) => line.trim()) || 'Image not pushed.'
  return sentence.endsWith('.') ? sentence : `${sentence}.`
}

export function renderReport(model) {
  const containerBody = explainContainer({
    event: model.event,
    ref: model.ref,
    dispatchJob: model.dispatchJob,
    result: model.jobs.find((job) => job.name === 'publish-container')?.result || '',
    summary: model.summaries.container,
  })
  const lines = [
    '# Dashboard CI report',
    '',
    testLead(model.tests),
    containerLead(model.summaries.container, containerBody),
    model.coverage.present ? `Coverage lines: ${model.coverage.lines}%.` : 'Coverage: no summary was collected.',
    'GitHub release: none. Delivery is the container image.',
    '',
    '## Run',
    '',
    `| | |`,
    `| --- | --- |`,
    `| Event | ${model.event || 'local'} |`,
    `| Ref | ${model.ref || 'n/a'} |`,
    `| Name | ${model.refName || 'n/a'} |`,
    `| Commit | ${model.sha || 'n/a'} |`,
    `| Dispatch job | ${model.dispatchJob || 'n/a'} |`,
    `| Repository | ${model.repository || 'n/a'} |`,
    `| Version | ${model.version || 'n/a'} |`,
    `| Image | ${model.imageName || 'n/a'} |`,
    `| Node | ${model.nodeVersion || 'n/a'} |`,
    '',
    '## Jobs',
    '',
    '| Job | Result |',
    '| --- | --- |',
    ...model.jobs.map((job) => `| ${job.name} | ${job.result} |`),
    '',
    '## Tests',
    '',
  ]
  if (!model.tests.present) {
    lines.push('No `test-results.json` was collected.', '')
  } else {
    lines.push(
      `${model.tests.passed} passed, ${model.tests.failed} failed, ${model.tests.pending} pending, ${model.tests.total} total.`,
    )
    if (model.tests.durationMs) lines.push(`Duration: ${model.tests.durationMs} ms.`)
    lines.push('Full output: `test-results.json`.', '')
    if (model.tests.failures.length > 0) {
      lines.push('Failed tests:', '')
      for (const failure of model.tests.failures) {
        lines.push(`- ${failure.name}`)
        if (failure.message) lines.push('', '```', failure.message.trim(), '```', '')
      }
    }
  }
  lines.push('## Coverage', '')
  if (!model.coverage.present) {
    lines.push('No `coverage-summary.json` was collected. Raw coverage files are copied when the test job uploaded them.', '')
  } else {
    lines.push(
      `| | percent |`,
      `| --- | --- |`,
      `| lines | ${model.coverage.lines} |`,
      `| statements | ${model.coverage.statements} |`,
      `| functions | ${model.coverage.functions} |`,
      `| branches | ${model.coverage.branches} |`,
      '',
      'Details: `coverage/`.',
      '',
    )
  }
  lines.push('## Setup', '', fence(model.summaries.setup) || 'No setup summary was collected.', '')
  if (model.audit) lines.push('npm audit:', '', '```', model.audit, '```', '')
  lines.push('## Build', '', fence(model.summaries.build) || 'No build summary was collected.', '')
  lines.push('## Docs', '', fence(model.summaries.docs) || 'No docs summary was collected.', '')
  lines.push('## Container publish', '', containerBody, '')
  lines.push('## Logs', '')
  if (model.logs.length === 0) lines.push('No make or script logs were collected.', '')
  else {
    lines.push('Make output and script output:', '')
    for (const log of model.logs) lines.push(`- \`logs/${log.bundleName || log.name}\``)
    lines.push('')
  }
  lines.push('## Bundle', '')
  if (!model.bundle?.length) lines.push('The report files are written next to this index.', '')
  else for (const file of model.bundle) lines.push(`- \`${file}\``)
  lines.push('')
  return `${lines.join('\n').replace(/\n{3,}/g, '\n\n')}\n`
}

function copyFile(from, to) {
  mkdirSync(path.dirname(to), { recursive: true })
  cpSync(from, to)
}

export function assemble({ root, env = process.env }) {
  const build = path.join(root, 'build')
  const out = path.join(build, 'report')
  rmSync(out, { recursive: true, force: true })
  mkdirSync(path.join(out, 'logs'), { recursive: true })
  const model = loadReport(root, env)
  const bundle = ['index.md']

  for (const log of model.logs) {
    const name = log.name.replace(/[^A-Za-z0-9._-]+/g, '_')
    log.bundleName = name
    copyFile(log.file, path.join(out, 'logs', name))
    bundle.push(`logs/${name}`)
  }
  if (model.testFile) {
    copyFile(model.testFile, path.join(out, 'test-results.json'))
    bundle.push('test-results.json')
  }
  if (model.coverageDir) {
    cpSync(model.coverageDir, path.join(out, 'coverage'), { recursive: true })
    bundle.push('coverage/')
  }
  for (const [key, filename] of [
    ['setup', 'setup.md'],
    ['build', 'build.md'],
    ['docs', 'docs.md'],
    ['container', 'publish-container.md'],
  ]) {
    if (!model.summaries[key]) continue
    const dest = path.join(out, 'summaries', filename)
    mkdirSync(path.dirname(dest), { recursive: true })
    writeFileSync(dest, model.summaries[key])
    bundle.push(`summaries/${filename}`)
  }
  model.bundle = bundle.sort()
  const markdown = renderReport(model)
  writeFileSync(path.join(out, 'index.md'), markdown)
  writeFileSync(path.join(build, 'report.md'), markdown)
  return markdown
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isMain) {
  try {
    process.stdout.write(assemble({ root: path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..') }))
  } catch (error) {
    console.error(error.message || error)
    process.exit(1)
  }
}
