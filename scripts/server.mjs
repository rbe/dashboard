import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { handleDashboardApi } from './dashboard-api.mjs'

const TYPES = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.ico': 'image/x-icon',
  '.woff': 'font/woff',
  '.woff2': 'font/woff2',
  '.txt': 'text/plain; charset=utf-8',
}

export function requestPathname(raw) {
  const value = String(raw || '/')
  const end = value.search(/[?#]/)
  const pathname = end === -1 ? value : value.slice(0, end)
  if (!pathname.startsWith('/')) return null
  return pathname
}

export function safeRelative(pathname) {
  if (typeof pathname !== 'string' || pathname.includes('\0')) return null
  let decoded
  try {
    decoded = decodeURIComponent(pathname)
  } catch {
    return null
  }
  if (decoded.includes('\0') || decoded.includes('\\')) return null
  if (decoded.split('/').includes('..')) return null
  const normalized = path.posix.normalize(decoded)
  const relative = normalized.replace(/^\/+/, '')
  if (!relative || relative === '.') return 'index.html'
  const parts = relative.split('/')
  if (parts.some((part) => part === '' || part === '..')) return null
  return relative
}

export function filesystemAssets(dist) {
  const resolved = path.resolve(dist)
  const root = fs.existsSync(resolved) ? fs.realpathSync(resolved) : resolved
  return (rel) => {
    if (typeof rel !== 'string' || rel.includes('\0')) return null
    const file = path.resolve(root, rel)
    let real
    try {
      real = fs.realpathSync(file)
    } catch {
      return null
    }
    if (real !== root && !real.startsWith(`${root}${path.sep}`)) return null
    if (!fs.statSync(real).isFile()) return null
    return fs.readFileSync(real)
  }
}

export function seaAssetReader(getAsset) {
  return (rel) => {
    if (typeof rel !== 'string' || rel.includes('\0') || rel.split('/').includes('..')) return null
    try {
      return Buffer.from(getAsset(rel))
    } catch {
      return null
    }
  }
}

function sendFile(res, method, file, body) {
  res.statusCode = 200
  res.setHeader('content-type', TYPES[path.posix.extname(file)] || 'application/octet-stream')
  res.setHeader('cache-control', 'no-store')
  res.setHeader('x-content-type-options', 'nosniff')
  res.end(method === 'HEAD' ? undefined : body)
}

export function startServer({ host, port, readAsset, store }) {
  const server = http.createServer((req, res) => {
    const pathname = requestPathname(req.url)
    if (!pathname) {
      res.statusCode = 400
      res.end('Bad request')
      return
    }
    if (pathname === '/api/dashboard') {
      handleDashboardApi(req, res, store)
      return
    }
    const relative = safeRelative(pathname)
    if (!relative) {
      res.statusCode = 403
      res.end('Forbidden')
      return
    }
    let file = relative
    let body
    try {
      body = readAsset(relative)
      if (body == null && relative !== 'index.html') {
        file = 'index.html'
        body = readAsset('index.html')
      }
    } catch {
      res.statusCode = 500
      res.end('Read failed')
      return
    }
    if (body == null) {
      res.statusCode = 404
      res.end('Not found')
      return
    }
    sendFile(res, req.method, file, body)
  })

  return new Promise((resolve, reject) => {
    const onError = (error) => {
      server.off('error', onError)
      reject(error)
    }
    server.on('error', onError)
    server.listen(port, host, () => {
      server.off('error', onError)
      resolve(server)
    })
  })
}
