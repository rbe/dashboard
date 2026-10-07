#!/usr/bin/env node
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { runDashboard } from '../scripts/cli.mjs'
import { filesystemAssets } from '../scripts/server.mjs'

const dist = path.resolve(fileURLToPath(new URL('../dist', import.meta.url)))
await runDashboard({ readAsset: filesystemAssets(dist) })
