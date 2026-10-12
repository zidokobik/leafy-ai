import { apiConfig } from './config'

type RequestOptions = Omit<RequestInit, 'body'> & {
  body?: unknown
  timeoutMs?: number
}

export class ApiError extends Error {
  readonly status: number
  readonly details: unknown

  constructor(message: string, status: number, details?: unknown) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.details = details
  }
}

/** The server's `detail` message for a failed request, or `fallback` when there is none. */
export function errorDetail(cause: unknown, fallback: string) {
  if (cause instanceof ApiError) {
    const detail = (cause.details as { detail?: unknown } | undefined)?.detail
    if (typeof detail === 'string') return detail
    if (cause.status === 408) return 'The request timed out. Refresh to check whether it went through.'
  }
  return fallback
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const controller = new AbortController()
  const abortFromCaller = () => controller.abort()
  options.signal?.addEventListener('abort', abortFromCaller, { once: true })
  if (options.signal?.aborted) controller.abort()
  const timeout = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? apiConfig.requestTimeoutMs,
  )

  try {
    const headers = new Headers(options.headers)
    headers.set('Accept', 'application/json')
    if (options.body !== undefined) headers.set('Content-Type', 'application/json')
    const response = await fetch(`${apiConfig.baseUrl}${path}`, {
      ...options,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: options.credentials ?? 'include',
      headers,
      signal: controller.signal,
    })


    if (!response.ok) {
      const details = await response.json().catch(() => undefined)
      throw new ApiError(`API request failed with status ${response.status}`, response.status, details)
    }

    if (response.status === 204) {
      return undefined as T
    }

    return await response.json() as T
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw new ApiError('API request timed out', 408)
    }
    throw new ApiError(error instanceof Error ? error.message : 'Unknown API error', 0)
  } finally {
    window.clearTimeout(timeout)
    options.signal?.removeEventListener('abort', abortFromCaller)
  }
}
