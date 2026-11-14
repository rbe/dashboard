import { createPrivateKey, X509Certificate } from 'node:crypto'
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { ensureServerCertificate, generateSelfSignedCertificate } from './tls-cert.mjs'

function pairDir() {
  const dir = mkdtempSync(path.join(tmpdir(), 'dashboard-tls-'))
  return {
    dir,
    certPath: path.join(dir, 'cert.pem'),
    keyPath: path.join(dir, 'key.pem'),
  }
}

describe('self-signed server certificate', () => {
  it('builds a localhost certificate that matches its private key', () => {
    const { cert, key } = generateSelfSignedCertificate()
    const parsed = new X509Certificate(cert)
    expect(parsed.verify(parsed.publicKey)).toBe(true)
    expect(parsed.checkPrivateKey(createPrivateKey(key))).toBe(true)
    expect(parsed.issuer).toBe(parsed.subject)
    expect(parsed.subject).toMatch(/localhost/)
    expect(parsed.ca).toBe(false)
    expect(parsed.subjectAltName).toMatch(/DNS:localhost/)
    expect(parsed.subjectAltName).toMatch(/127\.0\.0\.1/)
    expect(parsed.subjectAltName).toMatch(/0:0:0:0:0:0:0:1/)
  })

  it('creates a private key on first use and reuses it', () => {
    const paths = pairDir()
    try {
      const first = ensureServerCertificate(paths)
      expect(first.wrote).toBe(true)
      expect(statSync(paths.keyPath).mode & 0o777).toBe(0o600)
      expect(statSync(paths.certPath).mode & 0o777).toBe(0o644)
      const second = ensureServerCertificate(paths)
      expect(second.wrote).toBe(false)
      expect(Buffer.compare(first.cert, second.cert)).toBe(0)
      expect(readFileSync(paths.keyPath)).toEqual(first.key)
    } finally {
      rmSync(paths.dir, { recursive: true, force: true })
    }
  })

  it('replaces an expired certificate and keeps a mismatched key', () => {
    const paths = pairDir()
    try {
      const expired = generateSelfSignedCertificate({ now: new Date('2020-01-01T00:00:00Z'), days: 1 })
      writeFileSync(paths.certPath, expired.cert)
      writeFileSync(paths.keyPath, expired.key)
      const replaced = ensureServerCertificate({ ...paths, now: new Date('2026-01-01T00:00:00Z') })
      expect(replaced.wrote).toBe(true)
      expect(replaced.cert.equals(Buffer.from(expired.cert))).toBe(false)
      expect(new X509Certificate(replaced.cert).validTo).not.toContain('2020')

      const other = generateSelfSignedCertificate()
      writeFileSync(paths.certPath, other.cert)
      const keyBefore = readFileSync(paths.keyPath)
      expect(() => ensureServerCertificate(paths)).toThrow(/does not match/)
      expect(readFileSync(paths.keyPath)).toEqual(keyBefore)
      expect(readFileSync(paths.certPath, 'utf8')).toBe(other.cert)
    } finally {
      rmSync(paths.dir, { recursive: true, force: true })
    }
  })

  it('refuses a half-written or unreadable pair', () => {
    const paths = pairDir()
    try {
      writeFileSync(paths.certPath, 'not a certificate')
      expect(() => ensureServerCertificate(paths)).toThrow(/must both exist/)
      writeFileSync(paths.keyPath, 'not a key')
      expect(() => ensureServerCertificate(paths)).toThrow(/Invalid TLS certificate/)
      expect(readFileSync(paths.certPath, 'utf8')).toBe('not a certificate')
    } finally {
      rmSync(paths.dir, { recursive: true, force: true })
    }
  })
})
