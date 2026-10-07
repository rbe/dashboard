import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { collectAssets } from './build-binary.mjs'

describe('binary asset manifest', () => {
  it('keys files by their dist-relative path', () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-assets-'))
    try {
      mkdirSync(path.join(dir, 'assets'))
      writeFileSync(path.join(dir, 'index.html'), 'hi')
      writeFileSync(path.join(dir, 'assets', 'app.js'), 'js')
      const assets = collectAssets(dir)
      expect(assets['index.html']).toBe(path.join(dir, 'index.html'))
      expect(assets['assets/app.js']).toBe(path.join(dir, 'assets', 'app.js'))
      expect(() => collectAssets(path.join(dir, 'assets'))).toThrow(/index\.html/)
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
