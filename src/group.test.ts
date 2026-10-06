import { describe, expect, it } from 'vitest'
import { groupSystems, matches, moveWithinSubject } from './group'
import type { System } from './types'

function system(partial: Partial<System> & Pick<System, 'id' | 'name'>): System {
  return {
    subject: 'General',
    summary: '',
    note: '',
    task: '',
    tags: [],
    pinned: false,
    fields: {},
    links: [],
    ...partial,
  }
}

const systems = [
  system({ id: 'a', name: 'Alpha', subject: 'Mail', task: 'Operate', tags: ['mail', 'prod'], fields: { env: 'prod' } }),
  system({ id: 'b', name: 'Beta', subject: 'Mail', task: '', tags: [] }),
  system({ id: 'c', name: 'Gamma', subject: 'Development', task: 'Review', tags: ['prod'] }),
]

describe('grouping', () => {
  it('keeps subject order from the file', () => {
    expect(groupSystems(systems, 'subject').map((group) => group.key)).toEqual(['Mail', 'Development'])
  })

  it('groups by task with an empty bucket last', () => {
    const groups = groupSystems(systems, 'task')
    expect(groups.map((group) => group.key)).toEqual(['Operate', 'Review', ''])
  })

  it('repeats a system under each tag', () => {
    const groups = groupSystems(systems, 'tag')
    const mail = groups.find((group) => group.key === 'mail')
    const prod = groups.find((group) => group.key === 'prod')
    expect(mail?.systems.map((system) => system.id)).toEqual(['a'])
    expect(prod?.systems.map((system) => system.id)).toEqual(['a', 'c'])
    expect(groups.at(-1)?.key).toBe('')
  })

  it('groups by an extra field', () => {
    expect(groupSystems(systems, 'env').map((group) => [group.key, group.systems.length])).toEqual([
      ['prod', 1],
      ['', 2],
    ])
  })

  it('matches search across notes, tags, and urls', () => {
    const item = system({
      id: 'n',
      name: 'DNS',
      note: 'registrar login',
      tags: ['infra'],
      links: [{ label: 'AutoDNS', href: 'https://example.com/dns', role: '' }],
    })
    expect(matches(item, 'registrar', null)).toBe(true)
    expect(matches(item, 'autodns', null)).toBe(true)
    expect(matches(item, 'dns', 'infra')).toBe(true)
    expect(matches(item, 'dns', 'mail')).toBe(false)
  })

  it('moves a system among others in the same subject', () => {
    const moved = moveWithinSubject(systems, 'b', -1)
    expect(moved.map((system) => system.id)).toEqual(['b', 'a', 'c'])
  })
})
