import { getAsset, isSea } from 'node:sea'
import { runDashboard } from './cli.mjs'
import { seaAssetReader } from './server.mjs'

if (!isSea()) {
  console.error('This entry point only runs inside the packaged dashboard binary.')
  process.exit(1)
}

runDashboard({ readAsset: seaAssetReader(getAsset) }).catch((error) => {
  console.error(error && error.message ? error.message : error)
  process.exit(1)
})
