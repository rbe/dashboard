import { execFileSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import { createDashboardClient } from '../client/src/index.ts'
import { createStore, handleDashboardApi } from '../server/dashboard-api.mjs'
import { startServer } from '../server/server.mjs'
import { generateSelfSignedCertificate } from '../server/tls-cert.mjs'
import { validateRequest, validateResponse } from './validate.mjs'

const repo = fileURLToPath(new URL('..', import.meta.url))

function generator() {
  const candidates = [
    path.join(repo, 'node_modules', 'openapi-typescript'),
    path.join(repo, 'client', 'node_modules', 'openapi-typescript'),
  ]
  for (const dir of candidates) {
    const pkgPath = path.join(dir, 'package.json')
    try {
      const pkg = JSON.parse(readFileSync(pkgPath, 'utf8'))
      const bin = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin['openapi-typescript']
      return path.resolve(dir, bin)
    } catch {
      // The other install is used when this package is not present.
    }
  }
  throw new Error('openapi-typescript is not installed')
}

function response() {
  return {
    statusCode: 0,
    body: '',
    headers: {} as Record<string, string>,
    writableEnded: false,
    setHeader(key: string, value: string) {
      this.headers[key] = value
    },
    end(payload?: string) {
      this.body = payload ?? ''
      this.writableEnded = true
    },
  }
}

function put(raw: string) {
  return {
    method: 'PUT',
    on(event: string, cb: (chunk?: Buffer) => void) {
      if (event === 'data') cb(Buffer.from(raw))
      if (event === 'end') cb()
    },
  }
}

async function finish(res: { writableEnded: boolean }) {
  for (let i = 0; i < 50 && !res.writableEnded; i += 1) {
    await new Promise((resolve) => setTimeout(resolve, 10))
  }
}

describe('dashboard contract', () => {
  const spec = JSON.parse(readFileSync(path.join(repo, 'shared', 'openapi.json'), 'utf8'))

  it('commits types generated from the OpenAPI document', () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-schema-'))
    try {
      const out = path.join(dir, 'schema.ts')
      execFileSync(process.execPath, [generator(), path.join(repo, 'shared', 'openapi.json'), '-o', out], {
        encoding: 'utf8',
      })
      expect(readFileSync(out, 'utf8')).toBe(readFileSync(path.join(repo, 'shared', 'schema.ts'), 'utf8'))
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })

  it('describes only the board API and no authentication', () => {
    expect(spec.security).toEqual([])
    expect(spec.components.securitySchemes).toBeUndefined()
    expect(Object.keys(spec.paths)).toEqual(['/api/dashboard'])
    expect(Object.keys(spec.paths['/api/dashboard']).sort()).toEqual(['get', 'put'])
    expect(validateRequest('GET', undefined)).toBeNull()
    expect(validateRequest('PUT', { markdown: '# Board\n' })).toBeNull()
    expect(validateRequest('PUT', { markdown: 'x'.repeat(1_000_001) })).toMatch(/too long/)
    expect(validateResponse('GET', 200, { path: '/board.md', markdown: '' })).toBeNull()
    expect(validateResponse('PUT', 200, { ok: true })).toBeNull()
    expect(validateResponse('POST', 405, { error: 'method' })).toBeNull()
  })

  it('checks server replies and client calls against the spec', async () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-contract-'))
    const file = path.join(dir, 'board.md')
    const store = createStore(file)
    try {
      const read = response()
      handleDashboardApi({ method: 'GET' }, read, store)
      expect(read.statusCode).toBe(200)
      expect(validateResponse('GET', read.statusCode, JSON.parse(read.body))).toBeNull()

      const failed = response()
      handleDashboardApi({ method: 'GET' }, failed, {
        file,
        read() {
          throw new Error('nope')
        },
      })
      expect(JSON.parse(failed.body)).toEqual({ error: 'read-failed' })

      const invalid = response()
      handleDashboardApi(put('not-json'), invalid, store)
      await finish(invalid)
      expect(JSON.parse(invalid.body)).toEqual({ error: 'invalid-json' })

      const extra = response()
      handleDashboardApi(put(JSON.stringify({ markdown: '# Extra\n', note: 'kept' })), extra, store)
      await finish(extra)
      expect(extra.statusCode).toBe(200)
      expect(JSON.parse(extra.body)).toEqual({ ok: true })

      const denied = response()
      handleDashboardApi({ method: 'POST' }, denied, store)
      expect(JSON.parse(denied.body)).toEqual({ error: 'method' })

      const tls = generateSelfSignedCertificate()
      const server = await startServer({
        host: '127.0.0.1',
        port: 0,
        store,
        readAsset: () => null,
        cert: tls.cert,
        key: tls.key,
      })
      const { port } = server.address() as { port: number }
      try {
        const client = createDashboardClient({ baseUrl: `https://127.0.0.1:${port}`, ca: tls.cert })
        const loaded = await client.getDashboard()
        expect(loaded.path).toBe(file)
        expect(loaded.markdown).toContain('# Extra')
        expect(await client.putDashboard('# Reise\n')).toEqual({ ok: true })
        expect((await client.getDashboard()).markdown).toContain('# Reise')
      } finally {
        await new Promise((resolve) => server.close(() => resolve(undefined)))
      }
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
