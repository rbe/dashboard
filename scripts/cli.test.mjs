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
      help: false,
    })
    expect(parseDashboardArgs(['-h'], {}).help).toBe(true)
    expect(helpText()).toContain('--file')
  })

  it('lets flags override the environment', () => {
    const options = parseDashboardArgs(['--host=0.0.0.0', '--port', '8080', '--file', 'notes.md'], {
      PORT: '1',
      DASHBOARD_FILE: 'ignored.md',
    })
    expect(options.host).toBe('0.0.0.0')
    expect(options.port).toBe(8080)
    expect(options.file).toBe(path.resolve('notes.md'))
  })

  it('reads PORT and DASHBOARD_FILE', () => {
    const options = parseDashboardArgs([], { PORT: '9000', DASHBOARD_FILE: 'board.md' })
    expect(options.port).toBe(9000)
    expect(options.file).toBe(path.resolve('board.md'))
  })

  it('rejects unknown arguments and bad ports', () => {
    expect(() => parseDashboardArgs(['--port', 'nope'], {})).toThrow(/Invalid port/)
    expect(() => parseDashboardArgs(['--file'], {})).toThrow(/Missing value/)
    expect(() => parseDashboardArgs(['--extra'], {})).toThrow(/Unknown argument/)
  })

  it('prints help without a production build', () => {
    const result = spawnSync(process.execPath, ['bin/dashboard.mjs', '--help'], { encoding: 'utf8' })
    expect(result.status).toBe(0)
    expect(result.stdout).toContain('--file')
  })
})
