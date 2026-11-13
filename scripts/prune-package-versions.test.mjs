import { describe, expect, it } from 'vitest'
import {
  PACKAGE_VERSIONS_KEPT,
  deletePackageVersion,
  listPackageVersions,
  nextPageUrl,
  parseImageName,
  prunePackageVersions,
  selectVersionsToDelete,
} from './prune-package-versions.mjs'

function version({ id, created_at, tags }) {
  return { id, created_at, metadata: { container: { tags } } }
}

function jsonResponse(body, { status = 200, link = '' } = {}) {
  return {
    status,
    ok: status >= 200 && status < 300,
    headers: { get: (name) => (name.toLowerCase() === 'link' ? link : '') },
    json: async () => body,
    text: async () => JSON.stringify(body),
  }
}

describe('package version cleanup', () => {
  it('keeps the current version and exactly one former', () => {
    expect(PACKAGE_VERSIONS_KEPT).toBe(2)
    const versions = [
      version({ id: 1, created_at: '2026-01-01T00:00:00Z', tags: ['1.0.0-1'] }),
      version({ id: 4, created_at: '2026-01-04T00:00:00Z', tags: ['1.0.0-4'] }),
      version({ id: 2, created_at: '2026-01-02T00:00:00Z', tags: ['1.0.0-2'] }),
      version({ id: 5, created_at: '2026-01-05T00:00:00Z', tags: ['1.0.0-5', 'latest'] }),
      version({ id: 3, created_at: '2026-01-03T00:00:00Z', tags: ['1.0.0-3'] }),
    ]
    const decision = selectVersionsToDelete(versions, { currentTag: '1.0.0-5' })
    expect(decision.found).toBe(true)
    expect(decision.keep.map((item) => item.id)).toEqual([5, 4])
    expect(decision.delete.map((item) => item.id)).toEqual([3, 2, 1])
  })

  it('deletes nothing when only the current version exists', () => {
    const decision = selectVersionsToDelete([
      version({ id: 5, created_at: '2026-01-05T00:00:00Z', tags: ['1.0.0-5', 'latest'] }),
    ], { currentTag: '1.0.0-5' })
    expect(decision.keep.map((item) => item.id)).toEqual([5])
    expect(decision.delete).toEqual([])
  })

  it('deletes nothing when the current version and one former are the only versions', () => {
    const decision = selectVersionsToDelete([
      version({ id: 4, created_at: '2026-01-04T00:00:00Z', tags: ['1.0.0-4'] }),
      version({ id: 5, created_at: '2026-01-05T00:00:00Z', tags: ['1.0.0-5', 'latest'] }),
    ], { currentTag: '1.0.0-5' })
    expect(decision.keep.map((item) => item.id)).toEqual([5, 4])
    expect(decision.delete).toEqual([])
  })

  it('treats latest as a tag on the current version, not as a version to keep', () => {
    const decision = selectVersionsToDelete([
      version({ id: 1, created_at: '2026-01-01T00:00:00Z', tags: ['1.0.0-1'] }),
      version({ id: 2, created_at: '2026-01-02T00:00:00Z', tags: ['1.0.0-2'] }),
      version({ id: 3, created_at: '2026-01-03T00:00:00Z', tags: ['1.0.0-3', 'latest'] }),
    ], { currentTag: '1.0.0-3' })
    expect(decision.keep).toHaveLength(PACKAGE_VERSIONS_KEPT)
    expect(decision.delete.map((item) => item.id)).toEqual([1])
    expect(selectVersionsToDelete([
      version({ id: 3, created_at: '2026-01-03T00:00:00Z', tags: ['latest'] }),
    ], { currentTag: 'latest' }).found).toBe(false)
  })

  it('deletes nothing when the current tag is not the newest version', () => {
    const decision = selectVersionsToDelete([
      version({ id: 9, created_at: '2026-01-09T00:00:00Z', tags: ['latest'] }),
      version({ id: 8, created_at: '2026-01-08T00:00:00Z', tags: ['1.0.0-8'] }),
    ], { currentTag: '1.0.0-8' })
    expect(decision.found).toBe(false)
    expect(decision.delete).toEqual([])
  })

  it('breaks created_at ties by keeping the higher id', () => {
    const decision = selectVersionsToDelete([
      version({ id: 10, created_at: '2026-01-05T00:00:00Z', tags: ['1.0.0-10'] }),
      version({ id: 11, created_at: '2026-01-05T00:00:00Z', tags: ['1.0.0-11', 'latest'] }),
      version({ id: 9, created_at: '2026-01-04T00:00:00Z', tags: ['1.0.0-9'] }),
    ], { currentTag: '1.0.0-11' })
    expect(decision.keep.map((item) => item.id)).toEqual([11, 10])
    expect(decision.delete.map((item) => item.id)).toEqual([9])
  })

  it('parses the image name and the next page link', () => {
    expect(parseImageName('ghcr.io/Rbe/Dashboard')).toEqual({ owner: 'rbe', name: 'dashboard' })
    expect(() => parseImageName('ghcr.io/rbe/dashboard:latest')).toThrow(/Missing image name/)
    expect(nextPageUrl('<https://api.github.com/next>; rel="next", <https://api.github.com/last>; rel="last"')).toBe('https://api.github.com/next')
    expect(nextPageUrl('')).toBe('')
  })

  it('lists every page and deletes only versions older than the one former', async () => {
    const deleted = []
    const fetchImpl = async (url, options = {}) => {
      if (options.method === 'DELETE') {
        deleted.push(url)
        return jsonResponse({}, { status: 204 })
      }
      if (String(url).includes('/users/')) return jsonResponse({}, { status: 404 })
      if (String(url).includes('page=2')) {
        return jsonResponse([
          version({ id: 3, created_at: '2026-01-03T00:00:00Z', tags: ['1.0.0-3', 'latest'] }),
        ])
      }
      return jsonResponse([
        version({ id: 1, created_at: '2026-01-01T00:00:00Z', tags: ['1.0.0-1'] }),
        version({ id: 2, created_at: '2026-01-02T00:00:00Z', tags: ['1.0.0-2'] }),
      ], { link: '<https://api.github.com/orgs/rbe/packages/container/dashboard/versions?per_page=100&page=2>; rel="next"' })
    }
    const result = await prunePackageVersions({
      imageName: 'ghcr.io/rbe/dashboard',
      token: 'test-token',
      currentTag: '1.0.0-3',
      fetchImpl,
      attempts: 1,
    })
    expect(result.kept.map((item) => item.id)).toEqual([3, 2])
    expect(result.deleted.map((item) => item.id)).toEqual([1])
    expect(result.reason).toContain('exactly one former')
    expect(result.reason).toContain('not another package version')
    expect(deleted).toEqual([
      'https://api.github.com/orgs/rbe/packages/container/dashboard/versions/1',
    ])
  })

  it('does not delete when the current tag is absent', async () => {
    let deletes = 0
    const fetchImpl = async (url, options = {}) => {
      if (options.method === 'DELETE') deletes += 1
      expect(options.headers.Authorization).toBe('Bearer test-token')
      if (String(url).includes('/users/')) {
        return jsonResponse([
          version({ id: 2, created_at: '2026-01-02T00:00:00Z', tags: ['1.0.0-2', 'latest'] }),
        ])
      }
      throw new Error(`unexpected ${url}`)
    }
    await expect(prunePackageVersions({
      imageName: 'ghcr.io/rbe/dashboard',
      token: 'test-token',
      currentTag: '1.0.0-9',
      fetchImpl,
      attempts: 2,
      delayMs: 0,
      sleep: async () => {},
    })).rejects.toThrow(/Deleted nothing/)
    expect(deletes).toBe(0)
  })

  it('fails the cleanup when an older version cannot be deleted', async () => {
    const fetchImpl = async (url, options = {}) => {
      if (options.method === 'DELETE') return jsonResponse({ message: 'denied' }, { status: 500 })
      return jsonResponse([
        version({ id: 1, created_at: '2026-01-01T00:00:00Z', tags: ['1.0.0-1'] }),
        version({ id: 2, created_at: '2026-01-02T00:00:00Z', tags: ['1.0.0-2'] }),
        version({ id: 3, created_at: '2026-01-03T00:00:00Z', tags: ['1.0.0-3', 'latest'] }),
      ])
    }
    await expect(prunePackageVersions({
      imageName: 'ghcr.io/rbe/dashboard',
      token: 'test-token',
      currentTag: '1.0.0-3',
      fetchImpl,
      attempts: 1,
    })).rejects.toThrow(/Failed to delete package versions 1/)
  })

  it('does not delete when listing package versions fails', async () => {
    let deletes = 0
    let calls = 0
    const fetchImpl = async (_url, options = {}) => {
      calls += 1
      if (options.method === 'DELETE') deletes += 1
      return jsonResponse({}, { status: 500 })
    }
    await expect(prunePackageVersions({
      imageName: 'ghcr.io/rbe/dashboard',
      token: 'test-token',
      currentTag: '1.0.0-3',
      fetchImpl,
      attempts: 3,
      sleep: async () => {
        throw new Error('should not retry')
      },
    })).rejects.toThrow(/GitHub package API 500/)
    expect(deletes).toBe(0)
    expect(calls).toBe(1)
  })

  it('does not call the API without the publish token', async () => {
    let calls = 0
    const fetchImpl = async () => {
      calls += 1
      return jsonResponse([])
    }
    await expect(prunePackageVersions({
      imageName: 'ghcr.io/rbe/dashboard',
      token: '',
      currentTag: '1.0.0-1',
      fetchImpl,
      attempts: 1,
    })).rejects.toThrow(/GHCR_TOKEN/)
    expect(calls).toBe(0)
  })

  it('uses the user package API when that owner is a user', async () => {
    const listed = await listPackageVersions({
      owner: 'rbe',
      name: 'dashboard',
      token: 'test-token',
      fetchImpl: async (url) => {
        expect(url).toContain('/users/rbe/packages/container/dashboard/versions')
        return jsonResponse([
          version({ id: 1, created_at: '2026-01-01T00:00:00Z', tags: ['1.0.0-1'] }),
        ])
      },
    })
    expect(listed.api).toBe('users')
    let method = ''
    await deletePackageVersion({
      api: listed.api,
      owner: 'rbe',
      name: 'dashboard',
      id: 1,
      token: 'test-token',
      fetchImpl: async (url, options) => {
        method = options.method
        expect(url).toBe('https://api.github.com/users/rbe/packages/container/dashboard/versions/1')
        return jsonResponse({}, { status: 204 })
      },
    })
    expect(method).toBe('DELETE')
  })
})
