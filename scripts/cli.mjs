import path from 'node:path'
import { createStore } from './dashboard-api.mjs'
import { startServer } from './server.mjs'

export function helpText() {
  return `dashboard — local markdown dashboard

Usage:
  dashboard [--host 127.0.0.1] [--port 4173] [--file data/dashboard.md]

Options:
  --host      Address to bind. Default: 127.0.0.1
  --port      Port to listen on. Default: 4173, or PORT
  --file      Markdown file for the board. Default: data/dashboard.md, or DASHBOARD_FILE
  -h, --help  Show this help

The board stays in the markdown file you choose.`
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
    } else if (arg.startsWith('--host=')) {
      host = arg.slice('--host='.length)
    } else if (arg.startsWith('--port=')) {
      port = Number(arg.slice('--port='.length))
    } else if (arg.startsWith('--file=')) {
      file = arg.slice('--file='.length)
    } else {
      throw new Error(`Unknown argument: ${arg}`)
    }
  }

  if (!host) throw new Error('Missing value for --host')
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error(`Invalid port: ${port}`)
  if (!file) throw new Error('Missing value for --file')
  return { host, port, file: path.resolve(file), help }
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

  const store = createStore(options.file)
  let server
  try {
    server = await startServer({
      host: options.host,
      port: options.port,
      store,
      readAsset,
    })
  } catch (error) {
    console.error(error.code === 'EADDRINUSE' ? `Port ${options.port} is already in use` : error.message)
    process.exit(1)
  }

  const address = server.address()
  console.log(`Dashboard at http://${options.host}:${address.port}`)
  const stop = () => process.exit(0)
  process.once('SIGINT', stop)
  process.once('SIGTERM', stop)
  return server
}
