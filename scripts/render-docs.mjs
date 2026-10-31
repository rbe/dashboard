import { mkdirSync, readdirSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import path from 'node:path'

const source = argument('--source', 'docs')
const out = argument('--out', 'build/docs')

function argument(flag, fallback) {
  const index = process.argv.indexOf(flag)
  if (index === -1) return fallback
  const value = process.argv[index + 1]
  if (!value) throw new Error(`${flag} needs a path`)
  return value
}

function walk(dir, prefix = '') {
  let entries
  try {
    entries = readdirSync(dir)
  } catch (error) {
    if (error.code === 'ENOENT') return []
    throw error
  }
  const pages = []
  for (const name of entries) {
    if (name.startsWith('.')) continue
    const rel = prefix ? `${prefix}/${name}` : name
    const full = path.join(dir, name)
    if (statSync(full).isDirectory()) pages.push(...walk(full, rel))
    else if (name.endsWith('.md') || name.endsWith('.markdown')) pages.push(rel)
  }
  return pages
}

function escapeHtml(text) {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

function inline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '<a href="$2">$1</a>')
}

function renderMarkdown(markdown) {
  const lines = markdown.replaceAll('\r\n', '\n').split('\n')
  const html = []
  let index = 0
  while (index < lines.length) {
    const line = lines[index]
    if (line.startsWith('```')) {
      const body = []
      index += 1
      while (index < lines.length && !lines[index].startsWith('```')) {
        body.push(lines[index])
        index += 1
      }
      index += 1
      html.push(`<pre><code>${escapeHtml(body.join('\n'))}</code></pre>`)
      continue
    }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line)
    if (heading) {
      const level = heading[1].length
      html.push(`<h${level}>${inline(heading[2])}</h${level}>`)
      index += 1
      continue
    }
    if (/^\s*[-*]\s+/.test(line)) {
      const items = []
      while (index < lines.length && /^\s*[-*]\s+/.test(lines[index])) {
        items.push(`<li>${inline(lines[index].replace(/^\s*[-*]\s+/, ''))}</li>`)
        index += 1
      }
      html.push(`<ul>${items.join('')}</ul>`)
      continue
    }
    if (line.trim() === '') {
      index += 1
      continue
    }
    const paragraph = []
    while (
      index < lines.length &&
      lines[index].trim() !== '' &&
      !lines[index].startsWith('#') &&
      !lines[index].startsWith('```') &&
      !/^\s*[-*]\s+/.test(lines[index])
    ) {
      paragraph.push(lines[index])
      index += 1
    }
    html.push(`<p>${inline(paragraph.join(' '))}</p>`)
  }
  return html.join('\n')
}

function page(title, body) {
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${escapeHtml(title)}</title>
</head>
<body>
${body}
</body>
</html>
`
}

const pages = walk(source).sort()
if (pages.length === 0) {
  console.log('No docs to render. Skipping.')
  process.exit(0)
}

rmSync(out, { recursive: true, force: true })
for (const rel of pages) {
  const htmlName = rel.replace(/\.markdown$/, '.html').replace(/\.md$/, '.html')
  const dest = path.join(out, htmlName)
  mkdirSync(path.dirname(dest), { recursive: true })
  const title = path.basename(htmlName, '.html')
  writeFileSync(dest, page(title, renderMarkdown(readFileSync(path.join(source, rel), 'utf8'))))
}

const links = pages.map((rel) => {
  const htmlName = rel.replace(/\.markdown$/, '.html').replace(/\.md$/, '.html')
  return `<li><a href="${escapeHtml(htmlName)}">${escapeHtml(rel)}</a></li>`
})
writeFileSync(path.join(out, 'index.html'), page('Docs', `<h1>Docs</h1>\n<ul>\n${links.join('\n')}\n</ul>`))
console.log(`Rendered ${pages.length} docs to ${out}`)
