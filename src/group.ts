import type { System } from './types'

export type Group = {
  key: string
  systems: System[]
}

function facet(system: System, groupBy: string): string {
  if (groupBy === 'subject') return system.subject.trim() || 'General'
  if (groupBy === 'task') return system.task.trim()
  return (system.fields[groupBy] || '').trim()
}

function byAlpha(a: string, b: string): number {
  return a.localeCompare(b, undefined, { sensitivity: 'base' })
}

export function groupSystems(systems: System[], groupBy: string): Group[] {
  if (groupBy === 'tag') {
    const buckets = new Map<string, System[]>()
    const untagged: System[] = []
    for (const system of systems) {
      if (system.tags.length === 0) {
        untagged.push(system)
        continue
      }
      for (const tag of system.tags) {
        const list = buckets.get(tag)
        if (list) list.push(system)
        else buckets.set(tag, [system])
      }
    }
    const groups = [...buckets.keys()].sort(byAlpha).map((key) => ({
      key,
      systems: buckets.get(key) ?? [],
    }))
    if (untagged.length) groups.push({ key: '', systems: untagged })
    return groups
  }

  const order: string[] = []
  const buckets = new Map<string, System[]>()
  for (const system of systems) {
    const key = facet(system, groupBy)
    const list = buckets.get(key)
    if (list) list.push(system)
    else {
      buckets.set(key, [system])
      order.push(key)
    }
  }
  const keys =
    groupBy === 'subject'
      ? order
      : [...order.filter(Boolean).sort(byAlpha), ...order.filter((key) => !key)]
  return keys.map((key) => ({ key, systems: buckets.get(key) ?? [] }))
}

export function matches(system: System, query: string, tag: string | null): boolean {
  if (tag && !system.tags.some((item) => item.toLowerCase() === tag.toLowerCase())) return false
  const needle = query.trim().toLowerCase()
  if (!needle) return true
  const haystack = [
    system.name,
    system.summary,
    system.note,
    system.subject,
    system.task,
    system.tags.join(' '),
    ...Object.entries(system.fields).flat(),
    ...system.links.flatMap((link) => [link.label, link.href, link.role]),
  ]
    .join('\n')
    .toLowerCase()
  return haystack.includes(needle)
}

export function moveWithinSubject(systems: System[], id: string, direction: -1 | 1): System[] {
  const system = systems.find((item) => item.id === id)
  if (!system) return systems
  const siblings = systems.filter((item) => item.subject === system.subject)
  const position = siblings.findIndex((item) => item.id === id)
  const neighbor = siblings[position + direction]
  if (!neighbor) return systems
  const next = systems.slice()
  const from = next.findIndex((item) => item.id === id)
  const to = next.findIndex((item) => item.id === neighbor.id)
  ;[next[from], next[to]] = [next[to], next[from]]
  return next
}

export function fieldKeys(systems: System[]): string[] {
  const keys = new Set<string>()
  for (const system of systems) {
    for (const key of Object.keys(system.fields)) {
      if (system.fields[key]?.trim()) keys.add(key)
    }
  }
  return [...keys].sort(byAlpha)
}
