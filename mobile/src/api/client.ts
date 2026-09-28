import { apiBaseUrl } from './config'

const TIMEOUT_MS = 20_000

export type ApiErrorKind = 'network' | 'timeout' | 'http'

export class ApiError extends Error {
  constructor(
    readonly kind: ApiErrorKind,
    readonly status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

interface ClientHooks {
  getToken: () => string | null
  onUnauthorized: () => void
}

let hooks: ClientHooks = { getToken: () => null, onUnauthorized: () => undefined }

/** Connects the client to the session without an import cycle. */
export function configureClient(next: ClientHooks): void {
  hooks = next
}

function errorDetail(payload: unknown): string | undefined {
  if (!payload || typeof payload !== 'object' || !('detail' in payload)) return
  const { detail } = payload
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((issue: unknown) =>
      issue && typeof issue === 'object' && 'msg' in issue && typeof issue.msg === 'string'
        ? [issue.msg.replace(/^Value error, /, '')]
        : [],
    )
    return messages.length ? messages.join('. ') : undefined
  }
}

interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  json?: unknown
  form?: Record<string, string>
}

export async function api<T>(path: string, { method = 'GET', json, form }: RequestOptions = {}) {
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = hooks.getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let body: string | undefined
  if (json !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(json)
  } else if (form) {
    headers['Content-Type'] = 'application/x-www-form-urlencoded'
    body = new URLSearchParams(form).toString()
  }

  // AbortSignal.timeout is not available on every React Native runtime.
  const controller = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => {
    timedOut = true
    controller.abort()
  }, TIMEOUT_MS)
  let response: Response
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method,
      headers,
      body,
      signal: controller.signal,
    })
  } catch {
    throw timedOut
      ? new ApiError('timeout', 0, 'Request timed out')
      : new ApiError('network', 0, 'Network request failed')
  } finally {
    clearTimeout(timer)
  }

  const payload: unknown = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    if (response.status === 401 && token) hooks.onUnauthorized()
    throw new ApiError('http', response.status, errorDetail(payload) || `HTTP ${response.status}`)
  }
  return payload as T
}
