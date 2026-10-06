import { useState } from 'react'
import type { Messages } from './i18n'
import type { System } from './types'

type Actions = {
  groupBy: string
  activeTag: string | null
  showMove: boolean
  onEdit: (system: System) => void
  onMove: (id: string, direction: -1 | 1) => void
  onTag: (tag: string) => void
}

function details(system: System, groupBy: string): string {
  const parts: string[] = []
  if (groupBy !== 'subject' && system.subject) parts.push(system.subject)
  if (groupBy !== 'task' && system.task) parts.push(system.task)
  for (const [key, value] of Object.entries(system.fields)) {
    if (!value.trim() || key === groupBy) continue
    parts.push(`${key}: ${value}`)
  }
  return parts.join(' · ')
}

function Links({ system }: { system: System }) {
  if (system.links.length === 0) return null
  return (
    <div className="links">
      {system.links.map((link) => (
        <a key={`${link.href}-${link.label}`} href={link.href} target="_blank" rel="noopener noreferrer">
          {link.label}
          {link.role ? <span className="role">{link.role}</span> : null}
        </a>
      ))}
    </div>
  )
}

function Tags({ system, activeTag, onTag }: { system: System; activeTag: string | null; onTag: (tag: string) => void }) {
  if (system.tags.length === 0) return null
  return (
    <div className="tags">
      {system.tags.map((tag) => (
        <button
          key={tag}
          type="button"
          className={activeTag?.toLowerCase() === tag.toLowerCase() ? 'tag on' : 'tag'}
          onClick={() => onTag(tag)}
        >
          {tag}
        </button>
      ))}
    </div>
  )
}

function ActionsRow({ system, actions, t }: { system: System; actions: Actions; t: Messages }) {
  return (
    <div className="row-actions">
      <button type="button" onClick={() => actions.onEdit(system)}>
        {t.edit}
      </button>
      {actions.showMove ? (
        <>
          <button type="button" aria-label={t.up} onClick={() => actions.onMove(system.id, -1)}>
            ↑
          </button>
          <button type="button" aria-label={t.down} onClick={() => actions.onMove(system.id, 1)}>
            ↓
          </button>
        </>
      ) : null}
    </div>
  )
}

export function SystemCard({
  system,
  actions,
  t,
  compact = false,
}: {
  system: System
  actions: Actions
  t: Messages
  compact?: boolean
}) {
  const primary = system.links[0]
  const meta = details(system, actions.groupBy)
  return (
    <article className={system.pinned ? 'card pinned' : 'card'}>
      <header>
        {primary ? (
          <a className="name" href={primary.href} target="_blank" rel="noopener noreferrer">
            {system.name}
          </a>
        ) : (
          <h3 className="name">{system.name}</h3>
        )}
        <ActionsRow system={system} actions={actions} t={t} />
      </header>
      {compact ? null : (
        <>
          {system.summary ? <p className="summary">{system.summary}</p> : null}
          {system.note ? (
            <p className="note">
              <span>{t.noteOnCard}</span>
              {system.note}
            </p>
          ) : null}
          {meta ? <p className="meta">{meta}</p> : null}
          <Tags system={system} activeTag={actions.activeTag} onTag={actions.onTag} />
        </>
      )}
      {system.links.length ? <Links system={system} /> : <p className="muted">{t.noLinks}</p>}
    </article>
  )
}

export function SystemRow({ system, actions, t }: { system: System; actions: Actions; t: Messages }) {
  const meta = details(system, actions.groupBy)
  return (
    <article className="list-row">
      <div>
        <div className="name-line">
          {system.pinned ? <span className="pin" aria-label={t.pinned} /> : null}
          <strong>{system.name}</strong>
        </div>
        {meta ? <p className="meta">{meta}</p> : null}
      </div>
      <p className="summary">{system.summary || system.note}</p>
      <Links system={system} />
      <div className="list-side">
        <Tags system={system} activeTag={actions.activeTag} onTag={actions.onTag} />
        <ActionsRow system={system} actions={actions} t={t} />
      </div>
    </article>
  )
}

export function SystemFold({ system, actions, t }: { system: System; actions: Actions; t: Messages }) {
  const [open, setOpen] = useState(false)
  const meta = details(system, actions.groupBy)
  return (
    <article className="fold">
      <div className="fold-head">
        <button type="button" className="fold-toggle" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
          <span className={open ? 'chevron open' : 'chevron'} aria-hidden="true" />
          <span className="name">{system.name}</span>
          {system.summary ? <span className="summary">{system.summary}</span> : null}
        </button>
        <ActionsRow system={system} actions={actions} t={t} />
      </div>
      {open ? (
        <div className="fold-body">
          {system.note ? (
            <p className="note">
              <span>{t.noteOnCard}</span>
              {system.note}
            </p>
          ) : null}
          {meta ? <p className="meta">{meta}</p> : null}
          <Tags system={system} activeTag={actions.activeTag} onTag={actions.onTag} />
          {system.links.length ? <Links system={system} /> : <p className="muted">{t.noLinks}</p>}
        </div>
      ) : null}
    </article>
  )
}

export function groupLabel(groupBy: string, key: string, t: Messages): string {
  if (key) return key
  if (groupBy === 'task') return t.noTask
  if (groupBy === 'tag') return t.untagged
  return t.unset
}
