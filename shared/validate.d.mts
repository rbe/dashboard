export class ResponseContractError extends Error {}

export function validateRequest(method: string, body: unknown): string | null

export function validateResponse(method: string, status: number, body: unknown): string | null

export function assertResponse(method: string, status: number, body: unknown): void
