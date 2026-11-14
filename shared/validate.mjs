import spec from './openapi.json' with { type: 'json' }

const pathItem = spec.paths['/api/dashboard']

export class ResponseContractError extends Error {
  constructor(problem) {
    super(`Response does not match the OpenAPI spec: ${problem}`)
    this.name = 'ResponseContractError'
  }
}

function resolve(schema) {
  if (!schema.$ref) return schema
  const prefix = '#/components/schemas/'
  if (!schema.$ref.startsWith(prefix)) throw new Error(`Unsupported $ref: ${schema.$ref}`)
  const resolved = spec.components.schemas[schema.$ref.slice(prefix.length)]
  if (!resolved) throw new Error(`Missing schema: ${schema.$ref}`)
  return resolved
}

function same(left, right) {
  return left === right
}

function check(schema, value, at) {
  const node = resolve(schema)
  if (node.enum && !node.enum.some((item) => same(item, value))) {
    return `${at} is not an allowed value`
  }
  if (node.type === 'object') {
    if (value === null || typeof value !== 'object' || Array.isArray(value)) return `${at} must be an object`
    for (const key of node.required || []) {
      if (value[key] === undefined) return `${at} is missing ${key}`
    }
    const properties = node.properties || {}
    for (const [key, property] of Object.entries(properties)) {
      if (value[key] !== undefined) {
        const problem = check(property, value[key], `${at}.${key}`)
        if (problem) return problem
      }
    }
    if (node.additionalProperties === false) {
      for (const key of Object.keys(value)) {
        if (!Object.hasOwn(properties, key)) return `${at} has unexpected ${key}`
      }
    }
    return null
  }
  if (node.type === 'string') {
    if (typeof value !== 'string') return `${at} must be a string`
    if (node.maxLength != null && value.length > node.maxLength) return `${at} is too long`
    return null
  }
  if (node.type === 'boolean') {
    if (typeof value !== 'boolean') return `${at} must be a boolean`
    return null
  }
  return `${at} has an unsupported schema`
}

export function validateRequest(method, body) {
  const operation = pathItem[String(method).toLowerCase()]
  if (!operation) return `${method} is not an operation`
  const schema = operation.requestBody?.content?.['application/json']?.schema
  if (!schema) return body == null ? null : `${method} does not take a body`
  return check(schema, body, 'request')
}

export function validateResponse(method, status, body) {
  if (status === 405) return check(spec.components.schemas.MethodNotAllowed, body, 'response')
  const operation = pathItem[String(method).toLowerCase()]
  if (!operation) return `${method} is not an operation`
  const response = operation.responses[String(status)]
  const schema = response?.content?.['application/json']?.schema
  if (!schema) return `${method} ${status} is not in the spec`
  return check(schema, body, 'response')
}

export function assertResponse(method, status, body) {
  const problem = validateResponse(method, status, body)
  if (problem) throw new ResponseContractError(problem)
}
