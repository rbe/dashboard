// Self-signed server certificate built with Node crypto, so the server,
// the container, and the single-file binary do not need OpenSSL.
import {
  createPrivateKey,
  createSign,
  generateKeyPairSync,
  randomBytes,
  X509Certificate,
} from 'node:crypto'
import fs from 'node:fs'
import path from 'node:path'

const OID = {
  sha256WithRSAEncryption: '1.2.840.113549.1.1.11',
  commonName: '2.5.4.3',
  subjectAltName: '2.5.29.17',
  basicConstraints: '2.5.29.19',
  keyUsage: '2.5.29.15',
  extKeyUsage: '2.5.29.37',
  serverAuth: '1.3.6.1.5.5.7.3.1',
}

const CERT_DAYS = 397

function derLength(length) {
  if (length < 128) return Buffer.from([length])
  const bytes = []
  let value = length
  while (value > 0) {
    bytes.push(value & 0xff)
    value = Math.floor(value / 256)
  }
  bytes.reverse()
  return Buffer.from([0x80 | bytes.length, ...bytes])
}

function der(tag, content) {
  const body = Buffer.isBuffer(content) ? content : Buffer.from(content)
  return Buffer.concat([Buffer.from([tag]), derLength(body.length), body])
}

function seq(parts) {
  return der(0x30, Buffer.concat(parts))
}

function oid(dotted) {
  const arcs = dotted.split('.').map((part) => Number(part))
  const bytes = [40 * arcs[0] + arcs[1]]
  for (const arc of arcs.slice(2)) {
    const encoded = [arc & 0x7f]
    let value = Math.floor(arc / 128)
    while (value > 0) {
      encoded.push((value & 0x7f) | 0x80)
      value = Math.floor(value / 128)
    }
    bytes.push(...encoded.reverse())
  }
  return der(0x06, Buffer.from(bytes))
}

function unsignedInteger(buffer) {
  let body = buffer
  while (body.length > 1 && body[0] === 0x00 && (body[1] & 0x80) === 0) body = body.subarray(1)
  if (body.length === 0 || body[0] & 0x80) body = Buffer.concat([Buffer.from([0x00]), body])
  return der(0x02, body)
}

function algorithmIdentifier(dotted) {
  return seq([oid(dotted), Buffer.from([0x05, 0x00])])
}

function utcOrGeneralizedTime(date) {
  const pad = (value) => String(value).padStart(2, '0')
  const year = date.getUTCFullYear()
  const rest = `${pad(date.getUTCMonth() + 1)}${pad(date.getUTCDate())}${pad(date.getUTCHours())}${pad(date.getUTCMinutes())}${pad(date.getUTCSeconds())}Z`
  if (year >= 1950 && year <= 2049) return der(0x17, Buffer.from(`${pad(year % 100)}${rest}`))
  return der(0x18, Buffer.from(`${String(year)}${rest}`))
}

function commonName(value) {
  const attribute = seq([oid(OID.commonName), der(0x13, Buffer.from(value))])
  return seq([der(0x31, attribute)])
}

function extension(dotted, value, critical = false) {
  const parts = [oid(dotted)]
  if (critical) parts.push(Buffer.from([0x01, 0x01, 0xff]))
  parts.push(der(0x04, value))
  return seq(parts)
}

function subjectAltName() {
  return seq([
    der(0x82, Buffer.from('localhost')),
    der(0x87, Buffer.from([127, 0, 0, 1])),
    der(0x87, Buffer.from([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])),
  ])
}

function pem(label, body) {
  const base64 = body.toString('base64')
  const lines = []
  for (let offset = 0; offset < base64.length; offset += 64) lines.push(base64.slice(offset, offset + 64))
  return `-----BEGIN ${label}-----\n${lines.join('\n')}\n-----END ${label}-----\n`
}

export function generateSelfSignedCertificate({ now = new Date(), days = CERT_DAYS } = {}) {
  if (!Number.isInteger(days) || days < 1) throw new Error(`Invalid certificate lifetime: ${days}`)
  const { publicKey, privateKey } = generateKeyPairSync('rsa', {
    modulusLength: 2048,
    publicKeyEncoding: { type: 'spki', format: 'der' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  })
  const notBefore = new Date(now.getTime() - 5 * 60 * 1000)
  const notAfter = new Date(now.getTime() + days * 24 * 60 * 60 * 1000)
  const subject = commonName('localhost')
  const extensions = der(0xa3, seq([
    extension(OID.basicConstraints, seq([Buffer.from([0x01, 0x01, 0x00])])),
    extension(OID.keyUsage, der(0x03, Buffer.from([0x00, 0b10100000])), true),
    extension(OID.extKeyUsage, seq([oid(OID.serverAuth)])),
    extension(OID.subjectAltName, subjectAltName()),
  ]))
  const tbs = seq([
    der(0xa0, unsignedInteger(Buffer.from([2]))),
    unsignedInteger(randomBytes(16)),
    algorithmIdentifier(OID.sha256WithRSAEncryption),
    subject,
    seq([utcOrGeneralizedTime(notBefore), utcOrGeneralizedTime(notAfter)]),
    subject,
    publicKey,
    extensions,
  ])
  const signature = createSign('SHA256').update(tbs).sign(privateKey)
  const certificate = seq([
    tbs,
    algorithmIdentifier(OID.sha256WithRSAEncryption),
    der(0x03, Buffer.concat([Buffer.from([0x00]), signature])),
  ])
  return { cert: pem('CERTIFICATE', certificate), key: privateKey }
}

function inspectPair(certPem, keyPem, now) {
  let certificate
  let privateKey
  try {
    certificate = new X509Certificate(certPem)
  } catch {
    return { ok: false, reason: 'invalid-cert' }
  }
  try {
    privateKey = createPrivateKey(keyPem)
  } catch {
    return { ok: false, reason: 'invalid-key' }
  }
  if (!certificate.checkPrivateKey(privateKey)) return { ok: false, reason: 'mismatch' }
  if (now < new Date(certificate.validFrom) || now >= new Date(certificate.validTo)) {
    return { ok: false, reason: 'expired' }
  }
  return { ok: true }
}

function writePem(file, contents, mode) {
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, contents, { encoding: 'utf8', mode })
  fs.chmodSync(file, mode)
}

export function ensureServerCertificate({ certPath, keyPath, now = new Date() }) {
  const certExists = fs.existsSync(certPath)
  const keyExists = fs.existsSync(keyPath)
  if (certExists !== keyExists) {
    throw new Error(`TLS certificate and key must both exist (${certPath}, ${keyPath})`)
  }

  if (certExists) {
    const cert = fs.readFileSync(certPath)
    const key = fs.readFileSync(keyPath)
    const status = inspectPair(cert, key, now)
    if (status.ok) return { cert, key, wrote: false }
    if (status.reason === 'invalid-cert') throw new Error(`Invalid TLS certificate (${certPath})`)
    if (status.reason === 'invalid-key') throw new Error(`Invalid TLS private key (${keyPath})`)
    if (status.reason === 'mismatch') {
      throw new Error(`TLS certificate does not match the private key (${keyPath})`)
    }
  }

  const created = generateSelfSignedCertificate({ now })
  writePem(certPath, created.cert, 0o644)
  writePem(keyPath, created.key, 0o600)
  return {
    cert: fs.readFileSync(certPath),
    key: fs.readFileSync(keyPath),
    wrote: true,
  }
}
