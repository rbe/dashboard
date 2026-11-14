import { describe, expect, it, vi } from 'vitest'
import { createDashboardClient, DashboardClientError } from './index.ts'

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('dashboard client', () => {
  it('validates the request before sending and the reply after it arrives', async () => {
    const fetch = vi.fn(async () => jsonResponse(200, { ok: true }))
    const client = createDashboardClient({ baseUrl: 'https://board.example', fetch })
    await expect(client.putDashboard('x'.repeat(1_000_001))).rejects.toThrow(/OpenAPI spec/)
    expect(fetch).not.toHaveBeenCalled()

    fetch.mockResolvedValueOnce(jsonResponse(200, { path: '/board.md', markdown: '# Hi\n', extra: true }))
    await expect(client.getDashboard()).rejects.toThrow(/OpenAPI spec/)

    fetch.mockResolvedValueOnce(jsonResponse(400, { error: 'invalid-markdown' }))
    await expect(client.putDashboard('# Hi\n')).rejects.toBeInstanceOf(DashboardClientError)

    fetch.mockResolvedValueOnce(jsonResponse(200, { ok: true }))
    await expect(client.putDashboard('# Hi\n')).resolves.toEqual({ ok: true })
    expect(fetch).toHaveBeenCalledWith('https://board.example/api/dashboard', {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ markdown: '# Hi\n' }),
    })
  })

  it('rejects a reply that is not JSON', async () => {
    const fetch = vi.fn(async () => new Response('nope', { status: 200 }))
    const client = createDashboardClient({ baseUrl: 'https://board.example/', fetch })
    await expect(client.getDashboard()).rejects.toThrow(/not JSON/)
    expect(fetch).toHaveBeenCalledWith('https://board.example/api/dashboard', {
      method: 'GET',
      headers: undefined,
      body: undefined,
    })
  })
})
