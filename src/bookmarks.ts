import { sanitizeHref, uniqueId } from './markdown'
import type { System } from './types'

const GENERIC_FOLDERS = new Set([
  'bookmarks',
  'bookmarks bar',
  'bookmarks toolbar',
  'bookmark toolbar',
  'bookmarks menu',
  'other bookmarks',
  'mobile bookmarks',
  'unfiled bookmarks',
  'mozilla firefox',
  'lesezeichen',
  'lesezeichenleiste',
  'weitere lesezeichen',
])

function textOf(element: Element): string {
  return (element.textContent || '').replace(/\s+/g, ' ').trim()
}

function nearestDl(element: Element): Element | null {
  let parent = element.parentElement
  while (parent) {
    if (parent.tagName === 'DL') return parent
    parent = parent.parentElement
  }
  return null
}

function folderList(dt: Element): Element | null {
  const nested = [...dt.children].find((element) => element.tagName === 'DL')
  if (nested) return nested
  let next = dt.nextElementSibling
  while (next) {
    if (next.tagName === 'DL') return next
    if (next.tagName === 'DT') return null
    next = next.nextElementSibling
  }
  return null
}

function placement(stack: string[]): { subject: string; task: string } {
  const meaningful = stack.filter((name) => !GENERIC_FOLDERS.has(name.toLowerCase()))
  if (meaningful.length === 0) {
    return { subject: stack[stack.length - 1] || 'Imported', task: '' }
  }
  return {
    subject: meaningful[meaningful.length - 1],
    task: meaningful.slice(0, -1).join(' / '),
  }
}

function walk(dl: Element, stack: string[], into: System[]) {
  const entries = [...dl.querySelectorAll('dt')].filter((dt) => nearestDl(dt) === dl)
  for (const dt of entries) {
    const heading = dt.querySelector('h3')
    if (heading && heading.closest('dt') === dt) {
      const nested = folderList(dt)
      if (nested) walk(nested, [...stack, textOf(heading)], into)
      continue
    }
    const anchor = dt.querySelector('a')
    if (!anchor || anchor.closest('dt') !== dt) continue
    const href = sanitizeHref(anchor.getAttribute('href') || '')
    if (!href) continue
    const label = textOf(anchor) || href
    const place = placement(stack)
    into.push({
      id: '',
      name: label,
      subject: place.subject,
      summary: '',
      note: '',
      task: place.task,
      tags: [],
      pinned: false,
      fields: {},
      links: [{ label, href, role: '' }],
    })
  }
}

export function parseBookmarks(html: string): System[] {
  const document = new DOMParser().parseFromString(html, 'text/html')
  const root = document.querySelector('dl')
  if (!root) return []
  const systems: System[] = []
  walk(root, [], systems)
  return systems
}

export function importBookmarks(
  html: string,
  existing: System[],
): { systems: System[]; added: number; skipped: number; found: number } {
  const parsed = parseBookmarks(html)
  const hrefs = new Set(existing.flatMap((system) => system.links.map((link) => link.href)))
  const systems = existing.slice()
  let added = 0
  let skipped = 0
  for (const item of parsed) {
    const href = item.links[0]?.href
    if (!href || hrefs.has(href)) {
      skipped += 1
      continue
    }
    hrefs.add(href)
    systems.push({ ...item, id: uniqueId(item.name, systems) })
    added += 1
  }
  return { systems, added, skipped, found: parsed.length }
}
