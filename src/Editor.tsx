import { useEffect, useId, useRef, useState } from 'react'
import type { Messages } from './i18n'
import { isFieldKey, sanitizeHref } from './markdown'
import type { System } from './types'

type FieldRow = { key: string; value: string }
type LinkRow = { label: string; href: string; role: string }

type FormState = {
  name: string
  subject: string
  task: string
  summary: string
  note: string
  tags: string
  pinned: boolean
  fields: FieldRow[]
  links: LinkRow[]
}

function toForm(system: System): FormState {
  const fields = Object.entries(system.fields).map(([key, value]) => ({ key, value }))
  return {
    name: system.name,
    subject: system.subject,
    task: system.task,
    summary: system.summary,
    note: system.note,
    tags: system.tags.join(', '),
    pinned: system.pinned,
    fields,
    links: system.links.length ? system.links.map((link) => ({ ...link })) : [{ label: '', href: '', role: '' }],
  }
}

export function Editor({
  initial,
  systems,
  t,
  onSave,
  onDelete,
  onClose,
}: {
  initial: System
  systems: System[]
  t: Messages
  onSave: (system: System) => void
  onDelete: (id: string) => void
  onClose: () => void
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const formId = useId()
  const [form, setForm] = useState<FormState>(() => toForm(initial))
  const [error, setError] = useState('')
  const [confirming, setConfirming] = useState(false)
  const creating = initial.id === ''

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (!dialog.open) dialog.showModal()
    dialog.querySelector('input')?.focus()
    return () => {
      if (dialog.open) dialog.close()
    }
  }, [])

  const subjects = [...new Set(systems.map((system) => system.subject).filter(Boolean))]
  const tasks = [...new Set(systems.map((system) => system.task).filter(Boolean))]

  function save() {
    const name = form.name.trim()
    if (!name) {
      setError(t.required)
      return
    }
    const links = []
    for (const link of form.links) {
      const href = link.href.trim()
      const label = link.label.trim()
      if (!href && !label) continue
      const safe = sanitizeHref(href)
      if (!safe) {
        setError(t.badUrl)
        return
      }
      links.push({ label: label || safe, href: safe, role: link.role.trim().replace(/\s+/g, '') })
    }
    const fields: Record<string, string> = {}
    const seen = new Set<string>()
    for (const field of form.fields) {
      const key = field.key.trim().toLowerCase()
      const value = field.value.trim()
      if (!key && !value) continue
      if (!isFieldKey(key)) {
        setError(key && ['id', 'summary', 'note', 'task', 'tags', 'pinned', 'subject', 'name'].includes(key) ? t.reservedField : t.badField)
        return
      }
      if (seen.has(key)) {
        setError(t.duplicateField)
        return
      }
      seen.add(key)
      if (value) fields[key] = value
    }
    const draft: System = {
      ...initial,
      name,
      subject: form.subject.trim() || 'General',
      task: form.task.trim(),
      summary: form.summary.trim(),
      note: form.note.trim(),
      tags: form.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean)
        .filter((tag, index, all) => all.findIndex((item) => item.toLowerCase() === tag.toLowerCase()) === index),
      pinned: form.pinned,
      fields,
      links,
    }
    onSave(draft)
  }

  return (
    <dialog
      ref={dialogRef}
      aria-labelledby={`${formId}-title`}
      onCancel={(event) => {
        event.preventDefault()
        onClose()
      }}
      onClick={(event) => {
        if (event.target === dialogRef.current) onClose()
      }}
    >
      <form
        onSubmit={(event) => {
          event.preventDefault()
          save()
        }}
      >
        <header className="dialog-bar">
          <h2 id={`${formId}-title`}>{creating ? t.add : initial.name}</h2>
          {initial.id ? <code>{initial.id}</code> : null}
        </header>
        <div className="dialog-body">
          <label className="field">
            {t.name}
            <input value={form.name} autoComplete="off" onChange={(event) => setForm({ ...form, name: event.target.value })} />
          </label>
          <div className="split">
            <label className="field">
              {t.subject}
              <input
                value={form.subject}
                list={`${formId}-subjects`}
                autoComplete="off"
                onChange={(event) => setForm({ ...form, subject: event.target.value })}
              />
              <datalist id={`${formId}-subjects`}>
                {subjects.map((subject) => (
                  <option key={subject} value={subject} />
                ))}
              </datalist>
            </label>
            <label className="field">
              {t.task}
              <input
                value={form.task}
                list={`${formId}-tasks`}
                autoComplete="off"
                onChange={(event) => setForm({ ...form, task: event.target.value })}
              />
              <datalist id={`${formId}-tasks`}>
                {tasks.map((task) => (
                  <option key={task} value={task} />
                ))}
              </datalist>
            </label>
          </div>
          <label className="field">
            {t.summary}
            <input value={form.summary} autoComplete="off" onChange={(event) => setForm({ ...form, summary: event.target.value })} />
          </label>
          <label className="field">
            {t.note}
            <input value={form.note} autoComplete="off" onChange={(event) => setForm({ ...form, note: event.target.value })} />
          </label>
          <label className="field">
            {t.tags}
            <input
              value={form.tags}
              autoComplete="off"
              placeholder="ci, mail"
              onChange={(event) => setForm({ ...form, tags: event.target.value })}
            />
          </label>
          <label className="check">
            <input
              type="checkbox"
              checked={form.pinned}
              onChange={(event) => setForm({ ...form, pinned: event.target.checked })}
            />
            {t.pinnedLabel}
          </label>

          <div className="block-head">
            <h3>{t.fields}</h3>
            <button
              type="button"
              onClick={() => setForm({ ...form, fields: [...form.fields, { key: '', value: '' }] })}
            >
              {t.addField}
            </button>
          </div>
          <p className="hint">{t.fieldHint}</p>
          {form.fields.map((field, index) => (
            <div className="triple" key={index}>
              <input
                aria-label={t.fields}
                value={field.key}
                placeholder="env"
                autoComplete="off"
                onChange={(event) => {
                  const fields = form.fields.slice()
                  fields[index] = { ...field, key: event.target.value }
                  setForm({ ...form, fields })
                }}
              />
              <input
                aria-label={t.summary}
                value={field.value}
                autoComplete="off"
                onChange={(event) => {
                  const fields = form.fields.slice()
                  fields[index] = { ...field, value: event.target.value }
                  setForm({ ...form, fields })
                }}
              />
              <button
                type="button"
                onClick={() => setForm({ ...form, fields: form.fields.filter((_, item) => item !== index) })}
              >
                {t.remove}
              </button>
            </div>
          ))}

          <div className="block-head">
            <h3>{t.links}</h3>
            <button
              type="button"
              onClick={() => setForm({ ...form, links: [...form.links, { label: '', href: '', role: '' }] })}
            >
              {t.addLink}
            </button>
          </div>
          {form.links.map((link, index) => (
            <div className="triple links-edit" key={index}>
              <input
                aria-label={t.label}
                value={link.label}
                placeholder={t.label}
                autoComplete="off"
                onChange={(event) => {
                  const links = form.links.slice()
                  links[index] = { ...link, label: event.target.value }
                  setForm({ ...form, links })
                }}
              />
              <input
                aria-label={t.url}
                value={link.href}
                placeholder="https://"
                autoComplete="off"
                onChange={(event) => {
                  const links = form.links.slice()
                  links[index] = { ...link, href: event.target.value }
                  setForm({ ...form, links })
                }}
              />
              <input
                aria-label={t.role}
                value={link.role}
                placeholder={t.role}
                list={`${formId}-roles`}
                autoComplete="off"
                onChange={(event) => {
                  const links = form.links.slice()
                  links[index] = { ...link, role: event.target.value }
                  setForm({ ...form, links })
                }}
              />
              <button
                type="button"
                onClick={() => setForm({ ...form, links: form.links.filter((_, item) => item !== index) })}
              >
                {t.remove}
              </button>
            </div>
          ))}
          <datalist id={`${formId}-roles`}>
            {['console', 'status', 'docs', 'admin', 'mail'].map((role) => (
              <option key={role} value={role} />
            ))}
          </datalist>
          {error ? <p className="error">{error}</p> : null}
        </div>
        <footer className="dialog-bar">
          {creating ? (
            <span />
          ) : (
            <button
              type="button"
              className="danger"
              onClick={() => {
                if (!confirming) {
                  setConfirming(true)
                  return
                }
                onDelete(initial.id)
              }}
            >
              {confirming ? t.confirmDelete : t.delete}
            </button>
          )}
          <div className="dialog-actions">
            <button type="button" onClick={onClose}>
              {t.cancel}
            </button>
            <button type="submit" className="primary">
              {t.save}
            </button>
          </div>
        </footer>
      </form>
    </dialog>
  )
}
