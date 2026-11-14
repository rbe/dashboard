import { cpSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { createRequire } from 'node:module'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const clientDir = path.resolve(fileURLToPath(new URL('.', import.meta.url)))
const repo = path.resolve(clientDir, '..')
const stage = path.join(clientDir, 'type-stage')

function packageBin(name, binName = name) {
  const pkgJson = require.resolve(`${name}/package.json`)
  const pkg = require(pkgJson)
  const bin = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin[binName]
  return path.resolve(path.dirname(pkgJson), bin)
}

execFileSync(
  process.execPath,
  [packageBin('openapi-typescript'), path.join(repo, 'shared', 'openapi.json'), '-o', path.join(repo, 'shared', 'schema.ts')],
  { stdio: 'inherit' },
)

const esbuild = await import('esbuild')
await esbuild.build({
  entryPoints: [path.join(clientDir, 'src', 'index.ts')],
  bundle: true,
  platform: 'node',
  format: 'esm',
  target: 'node22',
  outfile: path.join(clientDir, 'dist', 'index.js'),
  legalComments: 'none',
})

rmSync(stage, { recursive: true, force: true })
mkdirSync(stage, { recursive: true })
const source = readFileSync(path.join(clientDir, 'src', 'index.ts'), 'utf8')
  .replaceAll("from '../../shared/schema.ts'", "from './schema.js'")
  .replaceAll("from '../../shared/validate.mjs'", "from './validate.mjs'")
writeFileSync(path.join(stage, 'index.ts'), source)
cpSync(path.join(repo, 'shared', 'schema.ts'), path.join(stage, 'schema.ts'))
cpSync(path.join(repo, 'shared', 'validate.d.mts'), path.join(stage, 'validate.d.mts'))
execFileSync(process.execPath, [packageBin('typescript', 'tsc'), '-p', 'tsconfig.build.json'], {
  cwd: clientDir,
  stdio: 'inherit',
})
rmSync(stage, { recursive: true, force: true })
