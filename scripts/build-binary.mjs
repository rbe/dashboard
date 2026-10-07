import { execFileSync } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { fileURLToPath } from 'node:url'

const require = createRequire(import.meta.url)
const root = path.resolve(fileURLToPath(new URL('..', import.meta.url)))
const buildDir = path.join(root, 'build')
const distDir = path.join(root, 'dist')

// Node's documented single-executable fuse. postject flips it so the
// runtime loads the embedded blob instead of starting the normal REPL.
const SEA_FUSE = 'NODE_SEA_FUSE_fce680ab2cc467b6e072b8b5df1996b2'

export function collectAssets(dist) {
  if (!fs.existsSync(dist)) throw new Error(`No index.html in ${dist}`)
  const assets = {}
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const abs = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(abs)
      else if (entry.isFile()) {
        assets[path.relative(dist, abs).split(path.sep).join('/')] = abs
      }
    }
  }
  walk(dist)
  if (!assets['index.html']) throw new Error(`No index.html in ${dist}`)
  return assets
}

function run(command, args, options = {}) {
  execFileSync(command, args, { stdio: 'inherit', ...options })
}

function postjectBin() {
  const pkgJson = require.resolve('postject/package.json')
  const pkg = require(pkgJson)
  const bin = typeof pkg.bin === 'string' ? pkg.bin : pkg.bin.postject
  return path.resolve(path.dirname(pkgJson), bin)
}

function inject(nodeBinary, outfile, platform) {
  fs.rmSync(outfile, { force: true })
  fs.copyFileSync(nodeBinary, outfile)
  fs.chmodSync(outfile, 0o755)
  const args = [outfile, 'NODE_SEA_BLOB', path.join(buildDir, 'sea-prep.blob'), '--sentinel-fuse', SEA_FUSE]
  if (platform === 'darwin') {
    run('codesign', ['--remove-signature', outfile])
    args.push('--macho-segment-name', 'NODE_SEA')
  }
  run(process.execPath, [postjectBin(), ...args])
  if (platform === 'darwin') run('codesign', ['--sign', '-', outfile])
}

async function downloadNodeBinary(version, platform, arch) {
  const folder = `node-${version}-${platform}-${arch}`
  const url = `https://nodejs.org/dist/${version}/${folder}.tar.gz`
  console.log(`Downloading ${url}`)
  const response = await fetch(url)
  if (!response.ok) throw new Error(`Failed to download ${url}: ${response.status}`)
  const archive = path.join(buildDir, `${folder}.tar.gz`)
  fs.writeFileSync(archive, Buffer.from(await response.arrayBuffer()))
  const dest = path.join(buildDir, 'node-dist')
  fs.mkdirSync(dest, { recursive: true })
  run('tar', ['-xzf', archive, '-C', dest, `${folder}/bin/node`])
  fs.rmSync(archive, { force: true })
  const binary = path.join(dest, folder, 'bin', 'node')
  const downloaded = execFileSync(binary, ['-p', 'process.version'], { encoding: 'utf8' }).trim()
  if (downloaded !== version) throw new Error(`Downloaded Node ${downloaded}, expected ${version}`)
  return binary
}

async function main() {
  const universal = process.argv.includes('--universal-macos')
  const major = Number(process.versions.node.split('.')[0])
  if (major < 22) throw new Error('Building the single binary requires Node.js 22 or newer.')
  if (universal && process.platform !== 'darwin') {
    throw new Error('--universal-macos must run on macOS so it can codesign and lipo the binary.')
  }
  if (!fs.existsSync(path.join(distDir, 'index.html'))) {
    throw new Error('dist/index.html is missing. Run npm run build first.')
  }

  fs.mkdirSync(buildDir, { recursive: true })
  const esbuild = await import('esbuild')
  const bundled = path.join(buildDir, 'sea-main.cjs')
  await esbuild.build({
    entryPoints: [path.join(root, 'scripts/sea-main.mjs')],
    bundle: true,
    platform: 'node',
    format: 'cjs',
    target: 'node22',
    outfile: bundled,
    external: ['node:sea'],
    legalComments: 'none',
    logLevel: 'info',
  })

  const configPath = path.join(buildDir, 'sea-config.json')
  const config = {
    main: bundled,
    output: path.join(buildDir, 'sea-prep.blob'),
    disableExperimentalSEAWarning: true,
    useSnapshot: false,
    useCodeCache: false,
    assets: collectAssets(distDir),
  }
  fs.writeFileSync(configPath, JSON.stringify(config))
  run(process.execPath, ['--experimental-sea-config', configPath])

  if (!universal) {
    const outfile = path.join(buildDir, 'dashboard')
    inject(fs.realpathSync(process.execPath), outfile, process.platform)
    console.log(`Wrote ${outfile}`)
    return
  }

  const version = process.version
  const arm = await downloadNodeBinary(version, 'darwin', 'arm64')
  const x64 = await downloadNodeBinary(version, 'darwin', 'x64')
  const armOut = path.join(buildDir, 'dashboard-darwin-arm64')
  const x64Out = path.join(buildDir, 'dashboard-darwin-x64')
  inject(arm, armOut, 'darwin')
  inject(x64, x64Out, 'darwin')
  const universalOut = path.join(buildDir, 'dashboard-macos')
  fs.rmSync(universalOut, { force: true })
  run('lipo', ['-create', '-output', universalOut, armOut, x64Out])
  run('codesign', ['--sign', '-', universalOut])
  fs.chmodSync(universalOut, 0o755)
  console.log(`Wrote ${universalOut}`)
}

const isMain = process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
if (isMain) {
  main().catch((error) => {
    console.error(error.message || error)
    process.exit(1)
  })
}
