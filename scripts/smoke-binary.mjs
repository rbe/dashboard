import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import http from 'node:http'
import net from 'node:net'
import { tmpdir } from 'node:os'
import path from 'node:path'

const command = process.argv[2]
if (!command) {
  console.error('Usage: node scripts/smoke-binary.mjs <dashboard-command>')
  process.exit(1)
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer()
    server.on('error', reject)
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close((error) => (error ? reject(error) : resolve(port)))
    })
  })
}

function request(port, pathname, options = {}) {
  return new Promise((resolve, reject) => {
    const req = http.request(
      {
        host: '127.0.0.1',
        port,
        path: pathname,
        method: options.method || 'GET',
        headers: options.headers,
      },
      (res) => {
        const chunks = []
        res.on('data', (chunk) => chunks.push(chunk))
        res.on('end', () => {
          resolve({
            status: res.statusCode,
            body: Buffer.concat(chunks).toString('utf8'),
            type: res.headers['content-type'] || '',
          })
        })
      },
    )
    req.on('error', reject)
    if (options.body) req.write(options.body)
    req.end()
  })
}

const port = await freePort()
const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-smoke-'))
const file = path.join(dir, 'board.md')
const child = spawn(path.resolve(command), ['--port', String(port), '--host', '127.0.0.1', '--file', file], {
  stdio: ['ignore', 'pipe', 'pipe'],
})
let logs = ''
child.stdout.on('data', (chunk) => {
  logs += chunk
})
child.stderr.on('data', (chunk) => {
  logs += chunk
})

try {
  const deadline = Date.now() + 20_000
  let ready = false
  let last = 'not started'
  while (Date.now() < deadline) {
    if (child.exitCode != null) throw new Error(`dashboard exited with ${child.exitCode}`)
    try {
      const home = await request(port, '/')
      if (home.status === 200) {
        ready = true
        if (!home.body.includes('id="root"')) throw new Error('index missing #root')
        const src = home.body.match(/src="([^"]+\.js)"/)
        if (!src) throw new Error('index missing script')
        const asset = await request(port, src[1])
        if (asset.status !== 200 || !asset.type.includes('javascript')) {
          throw new Error(`asset ${src[1]} returned ${asset.status} ${asset.type}`)
        }
        break
      }
      last = `status ${home.status}`
    } catch (error) {
      if (error.message.startsWith('index') || error.message.startsWith('asset')) throw error
      last = error.message
    }
    await new Promise((resolve) => setTimeout(resolve, 200))
  }
  if (!ready) throw new Error(`dashboard did not start (${last})`)

  const api = await request(port, '/api/dashboard')
  const saved = JSON.parse(api.body)
  if (api.status !== 200 || !saved.markdown.includes('not for git')) throw new Error('api read failed')
  const put = await request(port, '/api/dashboard', {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ markdown: '# Smoke\n\n## Box\nid: box\n' }),
  })
  if (put.status !== 200) throw new Error(`api write failed (${put.status})`)
  const again = JSON.parse((await request(port, '/api/dashboard')).body)
  if (!again.markdown.includes('# Smoke')) throw new Error('api write was not stored')
  const escaped = await request(port, '/%2e%2e/%2e%2e/etc/passwd')
  if (escaped.status !== 403 || escaped.body.includes('root:')) throw new Error('path traversal was not rejected')
  console.log(`Smoke test passed for ${command}`)
} catch (error) {
  console.error(error.message)
  if (logs.trim()) console.error(logs.trim())
  process.exitCode = 1
} finally {
  if (!child.killed) child.kill('SIGTERM')
  child.stdout.destroy()
  child.stderr.destroy()
  child.unref()
  rmSync(dir, { recursive: true, force: true })
}
