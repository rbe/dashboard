import path from 'node:path'
import { runDashboard } from './cli.mjs'
import { filesystemAssets } from './server.mjs'

await runDashboard({ readAsset: filesystemAssets(path.resolve('dist')) })
