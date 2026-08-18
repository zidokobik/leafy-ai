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

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!apiConfig.enabled) {
    throw new ApiError('VITE_API_BASE_URL is not configured', 0)
  }

  const controller = new AbortController()
  const abortFromCaller = () => controller.abort()
  options.signal?.addEventListener('abort', abortFromCaller, { once: true })
  const timeout = window.setTimeout(
    () => controller.abort(),
    options.timeoutMs ?? apiConfig.requestTimeoutMs,
  )

  try {
    const response = await fetch(`${apiConfig.baseUrl}${path}`, {
      ...options,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: options.credentials ?? 'include',
      headers: {
        Accept: 'application/json',
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
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
