import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { requireBuild, versionFromGitTag } from './container-tags.mjs'

// The version just published, plus exactly one former. `latest` is a tag on the newest version.
export const PACKAGE_VERSIONS_KEPT = 2

const RETRIES = 6
const RETRY_MS = 3000

export function parseImageName(imageName) {
  const image = String(imageName || '').trim().toLowerCase()
  const match = /^ghcr\.io\/([a-z0-9_.-]+)\/([a-z0-9_.-]+)$/.exec(image)
  if (!match) throw new Error('Missing image name')
  return { owner: match[1], name: match[2] }
}

export function packageTagNames(version) {
  const tags = version?.metadata?.container?.tags
  if (!Array.isArray(tags)) return []
  return tags.map((tag) => String(tag))
}

function createdAt(version) {
  const value = Date.parse(version?.created_at || '')
  return Number.isFinite(value) ? value : 0
}

function compareNewestFirst(a, b) {
  const delta = createdAt(b) - createdAt(a)
  if (delta !== 0) return delta
  return Number(b.id) - Number(a.id)
}

export function selectVersionsToDelete(versions, { currentTag } = {}) {
  const tag = String(currentTag || '')
  if (!tag || tag === 'latest') {
    return {
      found: false,
      keep: [],
      delete: [],
      reason: 'Refusing to treat latest as the published version. Deleted nothing.',
    }
  }
  const sorted = [...versions].sort(compareNewestFirst)
  const current = sorted.find((version) => packageTagNames(version).includes(tag))
  if (!current || sorted[0]?.id !== current.id) {
    return {
      found: false,
      keep: [],
      delete: [],
      reason: `Package version tagged ${tag} is not the newest version. Deleted nothing.`,
    }
  }
  const keep = sorted.slice(0, Math.min(PACKAGE_VERSIONS_KEPT, sorted.length))
  return { found: true, keep, delete: sorted.slice(keep.length), reason: '' }
}

export function pruneReason({ kept, deleted, currentTag }) {
  const removed = deleted.length
  const base = removed === 0
    ? (kept.length <= 1
      ? `One package version (${currentTag}) is published. Deleted nothing.`
      : `Kept the current ${currentTag} version and exactly one former. Deleted nothing.`)
    : `Kept the current ${currentTag} version and exactly one former. Deleted ${removed} older package ${removed === 1 ? 'version' : 'versions'}.`
  return `${base} latest is a tag on the newest version, not another package version.`
}

export function nextPageUrl(linkHeader) {
  if (!linkHeader) return ''
  for (const part of String(linkHeader).split(',')) {
    const match = part.match(/<([^>]+)>;\s*rel="next"/)
    if (match) return match[1]
  }
  return ''
}

function githubHeaders(token) {
  return {
    Accept: 'application/vnd.github+json',
    Authorization: `Bearer ${token}`,
    'X-GitHub-Api-Version': '2022-11-28',
  }
}

function headerValue(response, name) {
  const headers = response.headers
  if (!headers) return ''
  if (typeof headers.get === 'function') return headers.get(name) || headers.get(name.toLowerCase()) || ''
  return headers[name] || headers[name.toLowerCase()] || ''
}

async function collectPages(response, token, fetchImpl) {
  const versions = []
  let current = response
  const headers = githubHeaders(token)
  while (current) {
    if (!current.ok) {
      const error = new Error(`GitHub package API ${current.status}`)
      error.status = current.status
      throw error
    }
    const page = await current.json()
    if (!Array.isArray(page)) throw new Error('GitHub package version list was not an array.')
    versions.push(...page)
    const next = nextPageUrl(headerValue(current, 'link'))
    if (!next) return versions
    if (!next.startsWith('https://api.github.com/')) {
      throw new Error('Refusing a package version page outside api.github.com.')
    }
    current = await fetchImpl(next, { headers })
  }
  return versions
}

export async function listPackageVersions({ owner, name, token, fetchImpl }) {
  const packageName = encodeURIComponent(name)
  const encodedOwner = encodeURIComponent(owner)
  let last = null
  for (const api of ['users', 'orgs']) {
    const url = `https://api.github.com/${api}/${encodedOwner}/packages/container/${packageName}/versions?per_page=100`
    const response = await fetchImpl(url, { headers: githubHeaders(token) })
    if (response.status === 404) {
      last = new Error('GitHub package API 404')
      last.status = 404
      if (typeof response.body?.cancel === 'function') response.body.cancel()
      continue
    }
    const versions = await collectPages(response, token, fetchImpl)
    return { api, versions }
  }
  throw last
}

export async function deletePackageVersion({ api, owner, name, id, token, fetchImpl }) {
  const url = `https://api.github.com/${api}/${encodeURIComponent(owner)}/packages/container/${encodeURIComponent(name)}/versions/${id}`
  const response = await fetchImpl(url, { method: 'DELETE', headers: githubHeaders(token) })
  if ([200, 202, 204, 404].includes(response.status)) return
  const error = new Error(`GitHub package API ${response.status}`)
  error.status = response.status
  throw error
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export async function prunePackageVersions({
  imageName,
  token,
  currentTag,
  fetchImpl = globalThis.fetch,
  sleep = delay,
  attempts = RETRIES,
  delayMs = RETRY_MS,
} = {}) {
  if (!token) throw new Error('GHCR_TOKEN is required. Refusing to delete package versions.')
  const { owner, name } = parseImageName(imageName)
  let lastReason = `Package version tagged ${currentTag} is not the newest version. Deleted nothing.`
  for (let attempt = 1; attempt <= attempts; attempt += 1) {
    let listed
    try {
      listed = await listPackageVersions({ owner, name, token, fetchImpl })
    } catch (error) {
      if (error.status !== 404) throw error
      lastReason = `Package version tagged ${currentTag} was not listed. Deleted nothing.`
      if (attempt < attempts) {
        await sleep(delayMs)
        continue
      }
      throw new Error(lastReason)
    }
    const decision = selectVersionsToDelete(listed.versions, { currentTag })
    if (!decision.found) {
      lastReason = decision.reason
      if (attempt < attempts) {
        await sleep(delayMs)
        continue
      }
      throw new Error(lastReason)
    }
    const deleted = []
    const failures = []
    for (const version of decision.delete) {
      try {
        await deletePackageVersion({
          api: listed.api,
          owner,
          name,
          id: version.id,
          token,
          fetchImpl,
        })
        deleted.push(version)
      } catch (error) {
        failures.push(`${version.id} (${error.message})`)
      }
    }
    if (failures.length > 0) {
      const error = new Error(`Failed to delete package versions ${failures.join('; ')}.`)
      error.kept = decision.keep
      error.deleted = deleted
      throw error
    }
    return {
      kept: decision.keep,
      deleted,
      currentTag,
      reason: pruneReason({ kept: decision.keep, deleted, currentTag }),
    }
  }
  throw new Error(lastReason)
}

function redact(message, token) {
  const text = String(message || '').replace(/\s+/g, ' ').trim()
  if (!token) return text
  return text.split(token).join('[token]')
}

async function run() {
  const token = process.env.GHCR_TOKEN || process.env.GITHUB_TOKEN || ''
  try {
    const version = versionFromGitTag(process.env.GIT_TAG || '')
    const build = requireBuild(process.env.GITHUB_RUN_NUMBER || '')
    const currentTag = `${version}-${build}`
    const result = await prunePackageVersions({
      imageName: process.env.IMAGE_NAME || '',
      token,
      currentTag,
    })
    const status = result.deleted.length === 0 ? 'kept' : 'deleted'
    process.stdout.write([
      `status=${status}`,
      `kept=${result.kept.length}`,
      `deleted=${result.deleted.length}`,
      `kept_ids=${result.kept.map((version) => version.id).join(',')}`,
      `deleted_ids=${result.deleted.map((version) => version.id).join(',')}`,
      `reason=${result.reason}`,
      '',
    ].join('\n'))
  } catch (error) {
    const reason = redact(error.message || error, token)
    const kept = Array.isArray(error.kept) ? error.kept.length : 0
    const deleted = Array.isArray(error.deleted) ? error.deleted.length : 0
    process.stdout.write(`status=failed\nkept=${kept}\ndeleted=${deleted}\nreason=${reason}\n`)
    process.exit(1)
  }
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isMain) run()
