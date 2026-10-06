import { useEffect, useMemo, useRef, useState } from 'react'
import sampleMarkdown from '../data/dashboard.example.md?raw'
import { loadDashboard, saveDashboard } from './api'
import { groupLabel, SystemCard, SystemFold, SystemRow } from './board'
import { Editor } from './Editor'
import { importBookmarks } from './bookmarks'
import { fieldKeys, groupSystems, matches, moveWithinSubject } from './group'
import { messages } from './i18n'
import { blankSystem, parseDashboard, serializeDashboard, uniqueId } from './markdown'
import type { Lang, System, View } from './types'

const FORMAT = `# Subject

## System name
id: system-name
summary: What this is for
note: Optional private note
task: Optional task
tags: one, two
env: prod

- [Console](https://example.com) role=console`

function useStored(key: string, fallback: string) {
  const [value, setValue] = useState(() => localStorage.getItem(key) || fallback)
  useEffect(() => {
    localStorage.setItem(key, value)
  }, [key, value])
  return [value, setValue] as const
}

export function App() {
  const [lang, setLang] = useStored('aoc-dashboard.lang', navigator.language.toLowerCase().startsWith('de') ? 'de' : 'en')
  const [view, setView] = useStored('aoc-dashboard.view', 'cards')
  const [groupBy, setGroupBy] = useStored('aoc-dashboard.groupBy', 'subject')
  const [closed, setClosed] = useState<string[]>(() => {
    try {
      const raw = JSON.parse(localStorage.getItem('aoc-dashboard.closed') || '[]')
      return Array.isArray(raw) ? raw.filter((item) => typeof item === 'string') : []
    } catch {
      return []
    }
  })
  const [systems, setSystems] = useState<System[] | null>(null)
  const [filePath, setFilePath] = useState('')
  const [query, setQuery] = useState('')
  const [tag, setTag] = useState<string | null>(null)
  const [editor, setEditor] = useState<System | null>(null)
  const [status, setStatus] = useState('')
  const [error, setError] = useState('')
  const [loadError, setLoadError] = useState(false)
  const searchRef = useRef<HTMLInputElement>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const saveChain = useRef(Promise.resolve())
  const t = messages(lang === 'de' ? 'de' : 'en')
  const activeView: View = view === 'list' || view === 'collapse' ? view : 'cards'

  useEffect(() => {
    document.documentElement.lang = lang === 'de' ? 'de' : 'en'
    document.title = t.title
  }, [lang, t.title])

  useEffect(() => {
    localStorage.setItem('aoc-dashboard.closed', JSON.stringify(closed))
  }, [closed])

  useEffect(() => {
    void reload()
    // The file is only read once at startup. Reload is explicit after that.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target
      const typing =
        target instanceof HTMLElement &&
        (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
      if (event.key === '/' && !typing) {
        event.preventDefault()
        searchRef.current?.focus()
      }
      if ((event.key === 'n' || event.key === 'N') && !typing && !editor) {
        event.preventDefault()
        setEditor(blankSystem())
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [editor])

  async function reload() {
    try {
      const file = await loadDashboard()
      setFilePath(file.path)
      setSystems(parseDashboard(file.markdown))
      setLoadError(false)
      setError('')
    } catch {
      setLoadError(true)
    }
  }

  function persist(next: System[], doneMessage?: string) {
    setSystems(next)
    setStatus(t.saving)
    const markdown = serializeDashboard(next)
    const finished = doneMessage ?? t.saved
    saveChain.current = saveChain.current.then(async () => {
      try {
        await saveDashboard(markdown)
        setStatus(finished)
        setError('')
      } catch {
        setError(t.saveFailed)
        setStatus('')
      }
    })
  }

  function saveSystem(system: System) {
    const current = systems ?? []
    const index = current.findIndex((item) => item.id === system.id)
    const subject = system.subject.trim() || 'General'
    const next = current.slice()
    if (index >= 0) next[index] = { ...system, subject }
    else next.push({ ...system, id: uniqueId(system.name, next), subject })
    setEditor(null)
    persist(next)
  }

  const visible = useMemo(() => (systems ?? []).filter((system) => matches(system, query, tag)), [systems, query, tag])
  const pinned = visible.filter((system) => system.pinned)
  const options = fieldKeys(systems ?? [])
  const groupOptions = ['subject', 'task', 'tag', ...options]
  const activeGroup = groupOptions.includes(groupBy) ? groupBy : 'subject'
  const groups = groupSystems(visible, activeGroup)

  const actions = {
    groupBy: activeGroup,
    activeTag: tag,
    showMove: activeGroup === 'subject',
    onEdit: (system: System) => setEditor(system),
    onMove: (id: string, direction: -1 | 1) => {
      if (!systems) return
      persist(moveWithinSubject(systems, id, direction))
    },
    onTag: (next: string) => setTag((current) => (current?.toLowerCase() === next.toLowerCase() ? null : next)),
  }

  function renderSystem(system: System) {
    if (activeView === 'list') return <SystemRow key={system.id} system={system} actions={actions} t={t} />
    if (activeView === 'collapse') return <SystemFold key={system.id} system={system} actions={actions} t={t} />
    return <SystemCard key={system.id} system={system} actions={actions} t={t} />
  }

  return (
    <>
      <header className="topbar">
        <div className="wrap bar">
          <div className="brand">
            <span className="mark" aria-hidden="true" />
            <div>
              <h1>{t.title}</h1>
              <p>
                {t.subtitle}
                {systems ? <span> · {t.count(systems.length)}</span> : null}
              </p>
            </div>
          </div>
          <label className="search">
            <span className="sr">{t.search}</span>
            <input
              ref={searchRef}
              value={query}
              placeholder={`${t.search}  /`}
              onChange={(event) => setQuery(event.target.value)}
            />
          </label>
          <div className="controls">
            <div className="segment" role="group" aria-label={t.cards}>
              {(['cards', 'list', 'collapse'] as const).map((item) => (
                <button key={item} type="button" aria-pressed={activeView === item} onClick={() => setView(item)}>
                  {t[item]}
                </button>
              ))}
            </div>
            <label className="select">
              {t.groupBy}
              <select value={activeGroup} onChange={(event) => setGroupBy(event.target.value)}>
                {groupOptions.map((option) => (
                  <option key={option} value={option}>
                    {option === 'subject' ? t.subject : option === 'task' ? t.task : option === 'tag' ? t.tag : option}
                  </option>
                ))}
              </select>
            </label>
            <div className="segment" role="group" aria-label={t.language}>
              {(['en', 'de'] as const).map((item) => (
                <button key={item} type="button" aria-pressed={lang === item} onClick={() => setLang(item as Lang)}>
                  {item === 'en' ? 'EN' : 'DE'}
                </button>
              ))}
            </div>
            <button type="button" disabled={!systems} onClick={() => fileRef.current?.click()}>
              {t.importBookmarks}
            </button>
            <button type="button" disabled={!systems} onClick={() => {
              if ((systems?.length ?? 0) > 0 && !window.confirm(t.replaceSample)) return
              persist(parseDashboard(sampleMarkdown))
            }}>
              {t.sample}
            </button>
            <button type="button" className="primary" disabled={!systems} onClick={() => setEditor(blankSystem())}>
              {t.add}
            </button>
            <input
              ref={fileRef}
              className="sr-input"
              type="file"
              accept=".html,text/html"
              onChange={(event) => {
                const file = event.target.files?.[0]
                event.target.value = ''
                if (!file || !systems) return
                void file.text().then((html) => {
                  const result = importBookmarks(html, systems)
                  if (result.found === 0) {
                    setStatus(t.nothingImported)
                    return
                  }
                  persist(result.systems, t.imported(result.added, result.skipped))
                })
              }}
            />
          </div>
          {tag ? (
            <button type="button" className="tag on clear-tag" onClick={() => setTag(null)}>
              {tag} ×
            </button>
          ) : null}
          {status || error ? <p className={error ? 'error inline' : 'status'}>{error || status}</p> : null}
        </div>
      </header>
      <main className="wrap board">
        {loadError && !systems ? <p className="empty">{t.loadFailed}</p> : null}
        {systems && systems.length === 0 ? (
          <section className="empty">
            <h2>{t.emptyTitle}</h2>
            <p>{t.emptyBody}</p>
          </section>
        ) : null}
        {systems && systems.length > 0 && groups.length === 0 ? <p className="empty">{t.noMatches}</p> : null}
        {pinned.length > 0 ? (
          <section className="group">
            <h2 className="pinned-label">{t.pinned}</h2>
            <div className="cards">
              {pinned.map((system) => (
                <SystemCard key={system.id} system={system} actions={{ ...actions, showMove: false }} t={t} compact />
              ))}
            </div>
          </section>
        ) : null}
        {groups.map((group) => {
          const id = `${activeGroup}\u0000${group.key}`
          const isClosed = closed.includes(id)
          const label = groupLabel(activeGroup, group.key, t)
          return (
            <section className="group" key={id}>
              <button
                type="button"
                className="group-toggle"
                aria-expanded={!isClosed}
                onClick={() =>
                  setClosed((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]))
                }
              >
                <span className={isClosed ? 'chevron' : 'chevron open'} aria-hidden="true" />
                <span className="group-label">{label}</span>
                <span className="count">{group.systems.length}</span>
              </button>
              {isClosed ? null : <div className={activeView === 'cards' ? 'cards' : 'stack'}>{group.systems.map(renderSystem)}</div>}
            </section>
          )
        })}
      </main>
      <footer className="wrap foot">
        {filePath ? (
          <p>
            <span className="muted">{t.file}</span> <code title={filePath}>{filePath}</code>
          </p>
        ) : null}
        <p className="muted">{t.gitignored}</p>
        <div className="muted hand">
          {t.handEdit}{' '}
          <button type="button" className="text" onClick={() => void reload()}>
            {t.reload}
          </button>
        </div>
        <details>
          <summary>{t.format}</summary>
          <pre>{FORMAT}</pre>
        </details>
      </footer>
      {editor && systems ? (
        <Editor
          initial={editor}
          systems={systems}
          t={t}
          onSave={saveSystem}
          onDelete={(id) => {
            setEditor(null)
            persist((systems ?? []).filter((system) => system.id !== id))
          }}
          onClose={() => setEditor(null)}
        />
      ) : null}
    </>
  )
}
