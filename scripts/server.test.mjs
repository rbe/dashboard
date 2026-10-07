import { mkdirSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'node:fs'
import http from 'node:http'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { createStore } from './dashboard-api.mjs'
import { filesystemAssets, requestPathname, safeRelative, startServer } from './server.mjs'

function get(port, pathname) {
  return new Promise((resolve, reject) => {
    const req = http.request({ host: '127.0.0.1', port, path: pathname }, (res) => {
      const chunks = []
      res.on('data', (chunk) => chunks.push(chunk))
      res.on('end', () => {
        resolve({
          status: res.statusCode,
          body: Buffer.concat(chunks).toString('utf8'),
          type: res.headers['content-type'] || '',
        })
      })
    })
    req.on('error', reject)
    req.end()
  })
}

describe('dashboard server', () => {
  it('normalizes UI paths and rejects traversal', () => {
    expect(safeRelative('/')).toBe('index.html')
    expect(safeRelative('/assets/app.js')).toBe('assets/app.js')
    expect(safeRelative('/%2e%2e/%2e%2e/etc/passwd')).toBeNull()
    expect(safeRelative('/assets/%2e%2e/index.html')).toBeNull()
    expect(safeRelative(requestPathname('/%2e%2e/secret.txt?x=1'))).toBeNull()
    expect(requestPathname('/assets/app.js?v=1')).toBe('/assets/app.js')
  })

  it('serves the built UI and the board API from one port', async () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-server-'))
    const dist = path.join(dir, 'dist')
    try {
      mkdirSync(path.join(dist, 'assets'), { recursive: true })
      writeFileSync(path.join(dist, 'index.html'), '<div id="root"></div><script src="/assets/app.js"></script>')
      writeFileSync(path.join(dist, 'assets', 'app.js'), 'console.log(1)')
      writeFileSync(path.join(dir, 'secret.txt'), 'SECRET')
      symlinkSync(path.join(dir, 'secret.txt'), path.join(dist, 'leak.txt'))
      const readAsset = filesystemAssets(dist)
      expect(readAsset('leak.txt')).toBeNull()

      const server = await startServer({
        host: '127.0.0.1',
        port: 0,
        store: createStore(path.join(dir, 'board.md')),
        readAsset,
      })
      const { port } = server.address()
      try {
        const home = await get(port, '/')
        expect(home.status).toBe(200)
        expect(home.body).toContain('id="root"')
        expect(home.type).toContain('text/html')
        const asset = await get(port, '/assets/app.js')
        expect(asset.status).toBe(200)
        expect(asset.type).toContain('javascript')
        expect(asset.body).toContain('console.log')
        const escaped = await get(port, '/%2e%2e/secret.txt')
        expect(escaped.status).toBe(403)
        expect(escaped.body).not.toContain('SECRET')
        const missing = await get(port, '/missing')
        expect(missing.body).toContain('id="root"')

        const api = await get(port, '/api/dashboard')
        expect(api.status).toBe(200)
        expect(JSON.parse(api.body).markdown).toContain('not for git')
      } finally {
        await new Promise((resolve) => server.close(resolve))
      }
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
