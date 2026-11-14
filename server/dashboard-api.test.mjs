import { mkdtempSync, readFileSync, rmSync, statSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { createStore, handleDashboardApi } from './dashboard-api.mjs'

function response() {
  return {
    statusCode: 0,
    body: '',
    headers: {},
    writableEnded: false,
    setHeader(key, value) {
      this.headers[key] = value
    },
    end(payload) {
      this.body = payload
      this.writableEnded = true
    },
  }
}

describe('local dashboard store', () => {
  it('creates a private file and writes markdown in place', async () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-'))
    try {
      const file = path.join(dir, 'nested', 'dashboard.md')
      const store = createStore(file)
      expect(store.read()).toContain('not for git')
      expect(statSync(file).mode & 0o777).toBe(0o600)
      store.write('# Mail\n\n## Box\nid: box\n')
      expect(readFileSync(file, 'utf8')).toContain('# Mail')
      expect(() => store.write(12)).toThrow(/invalid-markdown/)
      expect(() => store.write('x'.repeat(1_000_001))).toThrow(/too-large/)

      const res = response()
      handleDashboardApi({ method: 'GET' }, res, store)
      expect(res.statusCode).toBe(200)
      expect(JSON.parse(res.body).path).toBe(file)

      const put = response()
      const payload = JSON.stringify({ markdown: '# Reise\n' })
      handleDashboardApi(
        {
          method: 'PUT',
          on(event, cb) {
            if (event === 'data') cb(Buffer.from(payload))
            if (event === 'end') cb()
          },
        },
        put,
        store,
      )
      await new Promise((resolve) => setTimeout(resolve, 20))
      expect(put.statusCode).toBe(200)
      expect(readFileSync(file, 'utf8')).toContain('# Reise')
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
