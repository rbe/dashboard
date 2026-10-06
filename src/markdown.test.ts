import { describe, expect, it } from 'vitest'
import sample from '../data/dashboard.example.md?raw'
import { parseDashboard, sanitizeHref, serializeDashboard } from './markdown'

describe('markdown dashboard', () => {
  it('reads the sample into systems with subjects, tasks, tags, and links', () => {
    const systems = parseDashboard(sample)
    expect(systems.map((system) => system.id)).toEqual(['teamcity', 'sonar', 'webmail', 'bahn'])
    const teamcity = systems[0]
    expect(teamcity.subject).toBe('Development')
    expect(teamcity.task).toBe('Operate')
    expect(teamcity.tags).toEqual(['ci', 'aoc'])
    expect(teamcity.pinned).toBe(true)
    expect(teamcity.fields.env).toBe('prod')
    expect(teamcity.links).toHaveLength(2)
    expect(teamcity.links[1].role).toBe('docs')
    expect(systems[3].subject).toBe('Reise')
  })

  it('round-trips without dropping fields', () => {
    const systems = parseDashboard(sample)
    const again = parseDashboard(serializeDashboard(systems))
    expect(again).toEqual(systems)
  })

  it('ignores comments and drops unsafe links', () => {
    const systems = parseDashboard(`
<!--
# Hidden
## Secret
-->
# Mail

## Admin
id: admin
summary: stays

- [Ok](https://example.com/admin)
- [Script](javascript:alert(1))
- [Password](https://user:secret@example.com)
`)
    expect(systems).toHaveLength(1)
    expect(systems[0].links.map((link) => link.href)).toEqual(['https://example.com/admin'])
  })

  it('rejects passwords and non-http urls', () => {
    expect(sanitizeHref('https://example.com/a')).toBe('https://example.com/a')
    expect(sanitizeHref('javascript:alert(1)')).toBeNull()
    expect(sanitizeHref('https://user:pw@example.com')).toBeNull()
  })

  it('keeps parentheses inside urls', () => {
    const systems = parseDashboard(`
# Docs

## Wiki
id: wiki

- [Foo](https://en.wikipedia.org/wiki/Foo_(bar)) role=docs
`)
    expect(systems[0].links[0].href).toBe('https://en.wikipedia.org/wiki/Foo_(bar)')
  })
})
