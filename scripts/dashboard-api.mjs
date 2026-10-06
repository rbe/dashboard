import fs from 'node:fs'
import path from 'node:path'

const MAX_CHARS = 1_000_000
const HEADER = '<!-- local dashboard data; not for git -->\n'

export function createStore(file) {
  return {
    file,
    read() {
      if (!fs.existsSync(file)) {
        fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 })
        fs.writeFileSync(file, HEADER, { encoding: 'utf8', mode: 0o600 })
      }
      return fs.readFileSync(file, 'utf8')
    },
    write(markdown) {
      if (typeof markdown !== 'string') throw new Error('invalid-markdown')
      if (markdown.length > MAX_CHARS) throw new Error('too-large')
      fs.mkdirSync(path.dirname(file), { recursive: true, mode: 0o700 })
      const tmp = `${file}.tmp`
      fs.writeFileSync(tmp, markdown.endsWith('\n') ? markdown : `${markdown}\n`, {
        encoding: 'utf8',
        mode: 0o600,
      })
      fs.renameSync(tmp, file)
      fs.chmodSync(file, 0o600)
    },
  }
}

export const store = createStore(
  process.env.DASHBOARD_FILE
    ? path.resolve(process.env.DASHBOARD_FILE)
    : path.resolve('data/dashboard.md'),
)

function send(res, code, body) {
  res.statusCode = code
  res.setHeader('content-type', 'application/json; charset=utf-8')
  res.setHeader('cache-control', 'no-store')
  res.setHeader('x-content-type-options', 'nosniff')
  res.end(JSON.stringify(body))
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0
    req.on('data', (chunk) => {
      size += chunk.length
      if (size > MAX_CHARS + 100_000) {
        reject(new Error('too-large'))
        req.destroy()
        return
      }
      chunks.push(chunk)
    })
    req.on('end', () => resolve(Buffer.concat(chunks).toString('utf8')))
    req.on('error', reject)
  })
}

export function handleDashboardApi(req, res, activeStore = store) {
  if (req.method === 'GET') {
    try {
      send(res, 200, { path: activeStore.file, markdown: activeStore.read() })
    } catch {
      send(res, 500, { error: 'read-failed' })
    }
    return
  }
  if (req.method === 'PUT') {
    readBody(req)
      .then((raw) => {
        let payload
        try {
          payload = JSON.parse(raw)
        } catch {
          send(res, 400, { error: 'invalid-json' })
          return
        }
        try {
          activeStore.write(payload.markdown)
        } catch {
          send(res, 400, { error: 'invalid-markdown' })
          return
        }
        send(res, 200, { ok: true })
      })
      .catch(() => {
        if (!res.writableEnded) send(res, 400, { error: 'invalid-body' })
      })
    return
  }
  send(res, 405, { error: 'method' })
}
