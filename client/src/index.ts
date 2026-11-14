import https from 'node:https'
import net from 'node:net'
import type { components } from '../../shared/schema.ts'
import { validateRequest, validateResponse } from '../../shared/validate.mjs'

export type DashboardFile = components['schemas']['DashboardFile']
export type DashboardWrite = components['schemas']['DashboardWrite']
export type DashboardSaved = components['schemas']['DashboardSaved']
export type DashboardProblem =
  | components['schemas']['ReadFailed']
  | components['schemas']['WriteFailed']
  | components['schemas']['MethodNotAllowed']

export class DashboardClientError extends Error {
  readonly status: number
  readonly body: DashboardProblem

  constructor(status: number, body: DashboardProblem) {
    super(body.error)
    this.name = 'DashboardClientError'
    this.status = status
    this.body = body
  }
}

export type DashboardClient = {
  getDashboard(): Promise<DashboardFile>
  putDashboard(markdown: string): Promise<DashboardSaved>
}

function headerRecord(headers: RequestInit['headers']) {
  if (!headers) return undefined
  if (headers instanceof Headers) return Object.fromEntries(headers.entries())
  if (Array.isArray(headers)) return Object.fromEntries(headers)
  return headers
}

export function fetchWithCertificate(ca: string): typeof fetch {
  return (async (input: string | URL | Request, init?: RequestInit) => {
    const url = new URL(typeof input === 'string' || input instanceof URL ? input : input.url)
    if (url.protocol !== 'https:') throw new Error('The dashboard certificate is only used with https')
    const body = typeof init?.body === 'string' ? init.body : undefined
    const payload = await new Promise<{ status: number; type: string; text: string }>((resolve, reject) => {
      const request = https.request(
        {
          hostname: url.hostname,
          port: url.port,
          path: `${url.pathname}${url.search}`,
          method: init?.method ?? 'GET',
          headers: headerRecord(init?.headers),
          ca,
          servername: net.isIP(url.hostname) ? undefined : url.hostname,
        },
        (response) => {
          const chunks: Buffer[] = []
          response.on('data', (chunk: Buffer) => chunks.push(chunk))
          response.on('end', () => {
            resolve({
              status: response.statusCode ?? 0,
              type: String(response.headers['content-type'] ?? ''),
              text: Buffer.concat(chunks).toString('utf8'),
            })
          })
        },
      )
      request.on('error', reject)
      if (body) request.write(body)
      request.end()
    })
    return new Response(payload.text, {
      status: payload.status,
      headers: payload.type ? { 'content-type': payload.type } : undefined,
    })
  }) as typeof fetch
}

async function readBody(response: Response) {
  const text = await response.text()
  try {
    return JSON.parse(text) as unknown
  } catch {
    throw new Error(`Response is not JSON (${response.status})`)
  }
}

async function call(
  fetchImpl: typeof fetch,
  baseUrl: string,
  method: 'GET' | 'PUT',
  payload?: DashboardWrite,
): Promise<DashboardFile | DashboardSaved> {
  const response = await fetchImpl(`${baseUrl}/api/dashboard`, {
    method,
    headers: payload ? { 'content-type': 'application/json' } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  })
  const body = await readBody(response)
  const problem = validateResponse(method, response.status, body)
  if (problem) throw new Error(`Response does not match the OpenAPI spec: ${problem}`)
  if (response.status === 200) return body as DashboardFile | DashboardSaved
  throw new DashboardClientError(response.status, body as DashboardProblem)
}

export function createDashboardClient(options: { baseUrl: string; fetch?: typeof fetch; ca?: string }): DashboardClient {
  const baseUrl = options.baseUrl.replace(/\/$/, '')
  const fetchImpl = options.fetch ?? (options.ca ? fetchWithCertificate(options.ca) : globalThis.fetch)
  return {
    getDashboard() {
      return call(fetchImpl, baseUrl, 'GET') as Promise<DashboardFile>
    },
    async putDashboard(markdown: string) {
      const payload: DashboardWrite = { markdown }
      const problem = validateRequest('PUT', payload)
      if (problem) throw new Error(`Request does not match the OpenAPI spec: ${problem}`)
      return call(fetchImpl, baseUrl, 'PUT', payload) as Promise<DashboardSaved>
    },
  }
}
