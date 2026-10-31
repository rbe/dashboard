import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const script = fileURLToPath(new URL('./render-docs.mjs', import.meta.url))

function render(source, out) {
  return execFileSync(process.execPath, [script, '--source', source, '--out', out], { encoding: 'utf8' })
}

describe('render docs', () => {
  it('writes html for markdown and an index', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'dashboard-docs-'))
    try {
      const source = path.join(root, 'docs')
      const out = path.join(root, 'html')
      mkdirSync(path.join(source, 'guide'), { recursive: true })
      writeFileSync(path.join(source, 'guide', 'start.md'), '# Start\n\nHello `there`.\n\n- one\n')
      const output = render(source, out)
      expect(output).toContain('Rendered 1 docs')
      const page = readFileSync(path.join(out, 'guide', 'start.html'), 'utf8')
      expect(page).toContain('<h1>Start</h1>')
      expect(page).toContain('<code>there</code>')
      expect(page).toContain('<li>one</li>')
      expect(page).not.toContain('AGENTS.md')
      const index = readFileSync(path.join(out, 'index.html'), 'utf8')
      expect(index).toContain('href="guide/start.html"')
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('escapes raw html in the source', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'dashboard-docs-'))
    try {
      const source = path.join(root, 'docs')
      const out = path.join(root, 'html')
      mkdirSync(source)
      writeFileSync(path.join(source, 'note.md'), '```\n<script>alert(1)</script>\n```\n')
      render(source, out)
      const page = readFileSync(path.join(out, 'note.html'), 'utf8')
      expect(page).toContain('&lt;script&gt;')
      expect(page).not.toContain('<script>alert')
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })

  it('skips when docs has no pages', () => {
    const root = mkdtempSync(path.join(tmpdir(), 'dashboard-docs-'))
    try {
      const source = path.join(root, 'missing')
      const out = path.join(root, 'html')
      const output = render(source, out)
      expect(output).toContain('No docs to render. Skipping.')
      expect(existsSync(out)).toBe(false)
    } finally {
      rmSync(root, { recursive: true, force: true })
    }
  })
})
