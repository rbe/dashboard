import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { handleDashboardApi } from './dashboard-api.mjs'

const dist = path.resolve('dist')
const host = '127.0.0.1'
const port = Number(process.env.PORT || 4173)
const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.json': 'application/json; charset=utf-8',
  '.map': 'application/json; charset=utf-8',
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url || '/', `http://${host}`)
  if (url.pathname === '/api/dashboard') {
    handleDashboardApi(req, res)
    return
  }
  const relative = path.normalize(decodeURIComponent(url.pathname)).replace(/^(\.\.[/\\])+/, '')
  let file = path.join(dist, relative)
  if (!file.startsWith(dist)) {
    res.statusCode = 403
    res.end('Forbidden')
    return
  }
  if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(dist, 'index.html')
  if (!fs.existsSync(file)) {
    res.statusCode = 404
    res.end('Not found')
    return
  }
  res.setHeader('content-type', types[path.extname(file)] || 'application/octet-stream')
  res.setHeader('cache-control', 'no-store')
  fs.createReadStream(file).pipe(res)
})

server.listen(port, host, () => {
  console.log(`Dashboard at http://${host}:${port}`)
})
