import { describe, expect, it } from 'vitest'
import { containerfileNodeVersion, formatGithubOutput, resolveImageTags } from './container-tags.mjs'

const sha = '0123456789abcdef0123456789abcdef01234567'

describe('container image tags', () => {
  it('publishes a release tag that matches package.json', () => {
    const result = resolveImageTags({
      imageName: 'ghcr.io/Rbe/Dashboard',
      ref: 'refs/tags/v1.2.3',
      refName: 'v1.2.3',
      sha,
      version: '1.2.3',
    })
    expect(result.publish).toBe(true)
    expect(result.image).toBe('ghcr.io/rbe/dashboard')
    expect(result.tags).toEqual([
      'ghcr.io/rbe/dashboard:1.2.3',
      'ghcr.io/rbe/dashboard:1.2',
      'ghcr.io/rbe/dashboard:1',
      'ghcr.io/rbe/dashboard:latest',
    ])
  })

  it('rejects a tag that does not match package.json', () => {
    expect(() =>
      resolveImageTags({
        imageName: 'ghcr.io/rbe/dashboard',
        ref: 'refs/tags/v1.2.3',
        refName: 'v1.2.3',
        sha,
        version: '1.0.0',
      }),
    ).toThrow(/does not match/)
  })

  it('publishes edge and a commit tag from master', () => {
    const result = resolveImageTags({
      imageName: 'ghcr.io/rbe/dashboard',
      ref: 'refs/heads/master',
      refName: 'master',
      sha,
      version: '1.0.0',
    })
    expect(result.publish).toBe(true)
    expect(result.tags).toEqual([
      'ghcr.io/rbe/dashboard:edge',
      'ghcr.io/rbe/dashboard:sha-0123456789ab',
    ])
  })

  it('does not publish pull requests', () => {
    const result = resolveImageTags({
      imageName: 'ghcr.io/rbe/dashboard',
      ref: 'refs/pull/9/merge',
      refName: '9/merge',
      sha,
      version: '1.0.0',
    })
    expect(result.publish).toBe(false)
    expect(result.tags).toEqual([])
    expect(formatGithubOutput(result)).toContain('publish=false')
    expect(formatGithubOutput(result)).toContain('tags=\n')
  })

  it('reads NODE_VERSION from the Containerfile', () => {
    expect(containerfileNodeVersion('ARG NODE_VERSION=24\nFROM node:${NODE_VERSION}-bookworm-slim\n')).toBe('24')
    expect(() => containerfileNodeVersion('FROM node:24\n')).toThrow(/NODE_VERSION/)
  })
})
