import { spawnSync } from 'node:child_process'
import path from 'node:path'
import { describe, expect, it } from 'vitest'
import { helpText, parseDashboardArgs } from './cli.mjs'

describe('dashboard cli', () => {
  it('defaults to the local board file', () => {
    expect(parseDashboardArgs([], {})).toEqual({
      host: '127.0.0.1',
      port: 4173,
      file: path.resolve('data/dashboard.md'),
      cert: path.resolve('data/tls/cert.pem'),
      key: path.resolve('data/tls/key.pem'),
      help: false,
    })
    expect(parseDashboardArgs(['-h'], {}).help).toBe(true)
    expect(helpText()).toContain('--file')
    expect(helpText()).toContain('--cert')
    expect(helpText()).toContain('self-signed')
  })

  it('lets flags override the environment', () => {
    const options = parseDashboardArgs(
      ['--host=0.0.0.0', '--port', '8080', '--file', 'notes.md', '--cert', 'c.pem', '--key=k.pem'],
      {
        PORT: '1',
        DASHBOARD_FILE: 'ignored.md',
        DASHBOARD_TLS_CERT: 'ignored-cert.pem',
        DASHBOARD_TLS_KEY: 'ignored-key.pem',
      },
    )
    expect(options.host).toBe('0.0.0.0')
    expect(options.port).toBe(8080)
    expect(options.file).toBe(path.resolve('notes.md'))
    expect(options.cert).toBe(path.resolve('c.pem'))
    expect(options.key).toBe(path.resolve('k.pem'))
  })

  it('reads PORT and DASHBOARD_FILE', () => {
    const options = parseDashboardArgs([], {
      PORT: '9000',
      DASHBOARD_FILE: 'board.md',
      DASHBOARD_TLS_CERT: 'tls/cert.pem',
      DASHBOARD_TLS_KEY: 'tls/key.pem',
    })
    expect(options.port).toBe(9000)
    expect(options.file).toBe(path.resolve('board.md'))
    expect(options.cert).toBe(path.resolve('tls/cert.pem'))
    expect(options.key).toBe(path.resolve('tls/key.pem'))
  })

  it('rejects unknown arguments and bad ports', () => {
    expect(() => parseDashboardArgs(['--port', 'nope'], {})).toThrow(/Invalid port/)
    expect(() => parseDashboardArgs(['--file'], {})).toThrow(/Missing value/)
    expect(() => parseDashboardArgs(['--cert'], {})).toThrow(/Missing value/)
    expect(() => parseDashboardArgs(['--extra'], {})).toThrow(/Unknown argument/)
  })

  it('prints help without a production build', () => {
    const result = spawnSync(process.execPath, ['bin/dashboard.mjs', '--help'], { encoding: 'utf8' })
    expect(result.status).toBe(0)
    expect(result.stdout).toContain('--file')
  })
})
