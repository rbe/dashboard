import type { Link, System } from './types'

export const RESERVED_FIELDS = new Set([
  'id',
  'summary',
  'note',
  'task',
  'tags',
  'pinned',
  'subject',
  'name',
])

const FIELD_KEY = /^[A-Za-z][A-Za-z0-9_-]*$/

export function slug(name: string): string {
  const value = name
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
  return value || 'system'
}

export function uniqueId(name: string, systems: System[]): string {
  const base = slug(name)
  const taken = new Set(systems.map((system) => system.id))
  let id = base
  let n = 2
  while (taken.has(id)) {
    id = `${base}-${n}`
    n += 1
  }
  return id
}

export function sanitizeHref(href: string): string | null {
  const trimmed = href.trim()
  if (!trimmed || /[\s<>]/.test(trimmed)) return null
  let url: URL
  try {
    url = new URL(trimmed)
  } catch {
    return null
  }
  if (url.protocol !== 'http:' && url.protocol !== 'https:') return null
  if (url.username || url.password) return null
  return trimmed
}

export function blankSystem(): System {
  return {
    id: '',
    name: '',
    subject: '',
    summary: '',
    note: '',
    task: '',
    tags: [],
    pinned: false,
    fields: {},
    links: [{ label: '', href: '', role: '' }],
  }
}

function emptySystem(name: string, subject: string): System {
  return {
    id: '',
    name,
    subject,
    summary: '',
    note: '',
    task: '',
    tags: [],
    pinned: false,
    fields: {},
    links: [],
  }
}

function parseTags(value: string): string[] {
  const tags: string[] = []
  const seen = new Set<string>()
  for (const part of value.split(',')) {
    const tag = part.trim()
    if (!tag) continue
    const key = tag.toLowerCase()
    if (seen.has(key)) continue
    seen.add(key)
    tags.push(tag)
  }
  return tags
}

function parseLink(line: string): Link | null {
  if (!line.startsWith('- [')) return null
  const roleMatch = line.match(/\s+role=(\S+)\s*$/)
  const role = roleMatch?.[1] ?? ''
  const body = roleMatch ? line.slice(0, roleMatch.index).trimEnd() : line
  const open = body.indexOf('](')
  if (!body.startsWith('- [') || open < 3 || !body.endsWith(')')) return null
  const label = body.slice(3, open).trim()
  const href = sanitizeHref(body.slice(open + 2, -1))
  if (!href) return null
  return { label: label || href, href, role }
}

function applyMeta(system: System, key: string, value: string) {
  if (key === 'id') {
    system.id = slug(value)
    return
  }
  if (key === 'summary') {
    system.summary = value
    return
  }
  if (key === 'note') {
    system.note = value
    return
  }
  if (key === 'task') {
    system.task = value
    return
  }
  if (key === 'tags') {
    system.tags = parseTags(value)
    return
  }
  if (key === 'pinned') {
    system.pinned = /^(true|yes|1)$/i.test(value)
    return
  }
  if (key === 'subject' || key === 'name') return
  system.fields[key] = value
}

export function parseDashboard(markdown: string): System[] {
  const systems: System[] = []
  let subject = 'General'
  let current: System | null = null
  let inComment = false

  const flush = () => {
    if (!current) return
    systems.push(current)
    current = null
  }

  for (const raw of markdown.replace(/\r\n/g, '\n').split('\n')) {
    const line = raw.trim()
    if (!inComment && line.includes('<!--')) {
      if (!line.includes('-->')) inComment = true
      continue
    }
    if (inComment) {
      if (line.includes('-->')) inComment = false
      continue
    }
    if (!line) continue
    if (line.startsWith('# ')) {
      flush()
      subject = line.slice(2).trim() || 'General'
      continue
    }
    if (line.startsWith('## ')) {
      flush()
      current = emptySystem(line.slice(3).trim() || 'Untitled', subject)
      continue
    }
    if (!current) continue
    const link = parseLink(line)
    if (link) {
      current.links.push(link)
      continue
    }
    const meta = line.match(/^([A-Za-z][A-Za-z0-9_-]*):\s*(.*)$/)
    if (meta) applyMeta(current, meta[1].toLowerCase(), meta[2].trim())
  }
  flush()

  const seen = new Set<string>()
  return systems.map((system) => {
    const base = system.id || slug(system.name)
    let id = base
    let n = 2
    while (seen.has(id)) {
      id = `${base}-${n}`
      n += 1
    }
    seen.add(id)
    return { ...system, id }
  })
}

function oneLine(value: string): string {
  return value.replace(/\s+/g, ' ').trim()
}

export function isFieldKey(key: string): boolean {
  return FIELD_KEY.test(key) && !RESERVED_FIELDS.has(key.toLowerCase())
}

export function serializeDashboard(systems: System[]): string {
  const lines = ['<!-- local dashboard data; not for git -->', '']
  const subjects: string[] = []
  for (const system of systems) {
    const subject = system.subject.trim() || 'General'
    if (!subjects.includes(subject)) subjects.push(subject)
  }
  for (const subject of subjects) {
    lines.push(`# ${subject}`, '')
    for (const system of systems) {
      if ((system.subject.trim() || 'General') !== subject) continue
      lines.push(`## ${oneLine(system.name) || 'Untitled'}`)
      lines.push(`id: ${system.id || slug(system.name)}`)
      if (system.summary.trim()) lines.push(`summary: ${oneLine(system.summary)}`)
      if (system.note.trim()) lines.push(`note: ${oneLine(system.note)}`)
      if (system.task.trim()) lines.push(`task: ${oneLine(system.task)}`)
      if (system.tags.length) lines.push(`tags: ${system.tags.join(', ')}`)
      if (system.pinned) lines.push('pinned: true')
      for (const key of Object.keys(system.fields).sort()) {
        const value = oneLine(system.fields[key] ?? '')
        if (!value || !isFieldKey(key)) continue
        lines.push(`${key.toLowerCase()}: ${value}`)
      }
      const links = system.links.filter((link) => sanitizeHref(link.href))
      if (links.length) lines.push('')
      for (const link of links) {
        const href = sanitizeHref(link.href)
        if (!href) continue
        const label = (link.label || href).replace(/[\[\]]/g, '').trim() || href
        const role = link.role.trim().replace(/\s+/g, '')
        lines.push(role ? `- [${label}](${href}) role=${role}` : `- [${label}](${href})`)
      }
      lines.push('')
    }
  }
  return `${lines.join('\n').replace(/\n{3,}/g, '\n\n').trimEnd()}\n`
}
