import path from 'node:path'
import { createStore } from './dashboard-api.mjs'
import { startServer } from './server.mjs'
import { ensureServerCertificate } from './tls-cert.mjs'

export function helpText() {
  return `dashboard — local markdown dashboard

Usage:
  dashboard [--host 127.0.0.1] [--port 4173] [--file data/dashboard.md]

Options:
  --host      Address to bind. Default: 127.0.0.1
  --port      Port to listen on. Default: 4173, or PORT
  --file      Markdown file for the board. Default: data/dashboard.md, or DASHBOARD_FILE
  --cert      PEM certificate. Default: data/tls/cert.pem, or DASHBOARD_TLS_CERT
  --key       PEM private key. Default: data/tls/key.pem, or DASHBOARD_TLS_KEY
  -h, --help  Show this help

The board stays in the markdown file you choose.
HTTPS uses a self-signed certificate, created when the cert and key are missing and replaced when it expires.`
}

function take(argv, index, flag) {
  const value = argv[index]
  if (value == null || value.startsWith('-')) throw new Error(`Missing value for ${flag}`)
  return value
}

export function parseDashboardArgs(argv, env = process.env) {
  let host = '127.0.0.1'
  let port = env.PORT ? Number(env.PORT) : 4173
  let file = env.DASHBOARD_FILE || path.join('data', 'dashboard.md')
  let cert = env.DASHBOARD_TLS_CERT || path.join('data', 'tls', 'cert.pem')
  let key = env.DASHBOARD_TLS_KEY || path.join('data', 'tls', 'key.pem')
  let help = false

  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i]
    if (arg === '--help' || arg === '-h') {
      help = true
    } else if (arg === '--host') {
      host = take(argv, (i += 1), arg)
    } else if (arg === '--port') {
      port = Number(take(argv, (i += 1), '--port'))
    } else if (arg === '--file') {
      file = take(argv, (i += 1), '--file')
    } else if (arg === '--cert') {
      cert = take(argv, (i += 1), arg)
    } else if (arg === '--key') {
      key = take(argv, (i += 1), arg)
    } else if (arg.startsWith('--host=')) {
      host = arg.slice('--host='.length)
    } else if (arg.startsWith('--port=')) {
      port = Number(arg.slice('--port='.length))
    } else if (arg.startsWith('--file=')) {
      file = arg.slice('--file='.length)
    } else if (arg.startsWith('--cert=')) {
      cert = arg.slice('--cert='.length)
    } else if (arg.startsWith('--key=')) {
      key = arg.slice('--key='.length)
    } else {
      throw new Error(`Unknown argument: ${arg}`)
    }
  }

  if (!host) throw new Error('Missing value for --host')
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error(`Invalid port: ${port}`)
  if (!file) throw new Error('Missing value for --file')
  if (!cert) throw new Error('Missing value for --cert')
  if (!key) throw new Error('Missing value for --key')
  return {
    host,
    port,
    file: path.resolve(file),
    cert: path.resolve(cert),
    key: path.resolve(key),
    help,
  }
}

export async function runDashboard({ argv = process.argv.slice(2), env = process.env, readAsset } = {}) {
  let options
  try {
    options = parseDashboardArgs(argv, env)
  } catch (error) {
    console.error(error.message)
    process.exit(1)
  }
  if (options.help) {
    console.log(helpText())
    return null
  }
  if (readAsset('index.html') == null) {
    console.error('Missing built dashboard (index.html). From a checkout, run npm run build.')
    process.exit(1)
  }

  let tls
  try {
    tls = ensureServerCertificate({ certPath: options.cert, keyPath: options.key })
  } catch (error) {
    console.error(error.message)
    process.exit(1)
  }
  if (tls.wrote) console.log(`Self-signed certificate ${options.cert}`)

  const store = createStore(options.file)
  let server
  try {
    server = await startServer({
      host: options.host,
      port: options.port,
      store,
      readAsset,
      cert: tls.cert,
      key: tls.key,
    })
  } catch (error) {
    console.error(error.code === 'EADDRINUSE' ? `Port ${options.port} is already in use` : error.message)
    process.exit(1)
  }

  const address = server.address()
  console.log(`Dashboard at https://${options.host}:${address.port}`)
  const stop = () => process.exit(0)
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  return server
}
