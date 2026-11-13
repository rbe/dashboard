import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { containerfileNodeVersion, formatGithubOutput, requireBuild, resolveImageTags, versionFromGitTag } from './container-tags.mjs'

describe('container image tags', () => {
  it('publishes the nearest release as version-run and latest', () => {
    const result = resolveImageTags({
      imageName: 'ghcr.io/Rbe/Dashboard',
      version: versionFromGitTag('v1.2.3'),
      build: '42',
    })
    expect(result.publish).toBe(true)
    expect(result.version).toBe('1.2.3')
    expect(result.build).toBe('42')
    expect(result.image).toBe('ghcr.io/rbe/dashboard')
    expect(result.tags).toEqual([
      'ghcr.io/rbe/dashboard:1.2.3-42',
      'ghcr.io/rbe/dashboard:latest',
    ])
    expect(formatGithubOutput(result)).toContain('publish=true')
    expect(formatGithubOutput(result)).toContain('tags=ghcr.io/rbe/dashboard:1.2.3-42,ghcr.io/rbe/dashboard:latest')
    expect(result.tags.some((tag) => tag.endsWith(':edge') || tag.includes('sha-'))).toBe(false)
    expect(result.tags).not.toContain('ghcr.io/rbe/dashboard:1.2.3')
  })

  it('strips a leading v and rejects tags that are not MAJOR.MINOR.PATCH', () => {
    expect(versionFromGitTag('v1.0.0')).toBe('1.0.0')
    expect(() => versionFromGitTag('')).toThrow(/Refusing to invent a version/)
    expect(() => versionFromGitTag('1.0.0')).toThrow(/not vMAJOR.MINOR.PATCH/)
    expect(() => versionFromGitTag('v1.0')).toThrow(/not vMAJOR.MINOR.PATCH/)
    expect(() => versionFromGitTag('v1.0.0-rc.1')).toThrow(/not vMAJOR.MINOR.PATCH/)
  })

  it('requires the GitHub run number and does not invent a build', () => {
    expect(requireBuild('7')).toBe('7')
    expect(() => requireBuild('')).toThrow(/Refusing to invent a build number/)
    expect(() => requireBuild('0')).toThrow(/Refusing to invent a build number/)
    expect(() => requireBuild('01')).toThrow(/Refusing to invent a build number/)
    expect(() => requireBuild('abc')).toThrow(/Refusing to invent a build number/)
    expect(() => resolveImageTags({
      imageName: 'ghcr.io/rbe/dashboard',
      version: '1.0.0',
      build: '',
    })).toThrow(/Refusing to invent a build number/)
  })

  it('fails instead of inventing a version', () => {
    expect(() => resolveImageTags({
      imageName: 'ghcr.io/rbe/dashboard',
      version: '',
      build: '7',
    })).toThrow(/Refusing to invent a version/)
    expect(() => resolveImageTags({
      imageName: 'ghcr.io/rbe/dashboard',
      version: '1.0.0-rc.1',
      build: '7',
    })).toThrow(/Refusing to invent a version/)
  })

  it('does not publish an edge tag or a sha tag', () => {
    const source = readFileSync(new URL('./container-tags.mjs', import.meta.url), 'utf8')
    expect(source).not.toContain('edge')
    expect(source).not.toContain('sha-')
    expect(source).toContain('GIT_TAG')
    expect(source).toContain('GITHUB_RUN_NUMBER')
  })

  it('reads NODE_VERSION from the Containerfile', () => {
    expect(containerfileNodeVersion('ARG NODE_VERSION=24\nFROM node:${NODE_VERSION}-bookworm-slim\n')).toBe('24')
    expect(() => containerfileNodeVersion('FROM node:24\n')).toThrow(/NODE_VERSION/)
  })
})
