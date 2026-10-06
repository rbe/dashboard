// @vitest-environment happy-dom
import { describe, expect, it } from 'vitest'
import { importBookmarks, parseBookmarks } from './bookmarks'
import type { System } from './types'

const html = `<!DOCTYPE NETSCAPE-Bookmark-file-1>
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3>Bookmarks bar</H3>
    <DL><p>
        <DT><A HREF="https://example.com/loose">Loose</A>
        <DT><H3>Work</H3>
        <DL><p>
            <DT><H3>Mail</H3>
            <DL><p>
                <DT><A HREF="https://mail.example.com/web?a=1&amp;b=2">A &amp; B</A>
                <DT><A HREF="javascript:alert(1)">Bad</A>
            </DL><p>
        </DL><p>
    </DL><p>
    <DT><H3>Other bookmarks</H3>
    <DL><p>
        <DT><A HREF="https://other.example/x">Other</A>
    </DL><p>
</DL><p>`

describe('bookmark import', () => {
  it('maps folders to subject and task and skips unsafe urls', () => {
    const systems = parseBookmarks(html)
    expect(systems.map((system) => [system.name, system.subject, system.task])).toEqual([
      ['Loose', 'Bookmarks bar', ''],
      ['A & B', 'Mail', 'Work'],
      ['Other', 'Other bookmarks', ''],
    ])
    expect(systems[1].links[0].href).toBe('https://mail.example.com/web?a=1&b=2')
  })

  it('merges into an existing board and skips duplicate urls', () => {
    const existing: System[] = [
      {
        id: 'mail',
        name: 'Already',
        subject: 'Mail',
        summary: '',
        note: '',
        task: '',
        tags: [],
        pinned: false,
        fields: {},
        links: [{ label: 'Web', href: 'https://mail.example.com/web?a=1&b=2', role: '' }],
      },
    ]
    const result = importBookmarks(html, existing)
    expect(result.added).toBe(2)
    expect(result.skipped).toBe(1)
    expect(result.systems.map((system) => system.id)).toEqual(['mail', 'loose', 'other'])
  })
})
