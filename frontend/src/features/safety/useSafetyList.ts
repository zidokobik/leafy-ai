import { useEffect, useState } from 'react'
import { ApiError } from '@/api/client'

export function safetyError(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Your session has expired. Please sign in again.'
    if (error.status === 409) return 'The record changed or already exists. Refresh and check before retrying.'
    if (error.status === 404) return 'The device or record was not found. Check its ID and refresh.'
  }
  return error instanceof Error ? error.message : 'Unable to complete the request.'
}

export function useSafetyList<T>(load: (offset: number, signal: AbortSignal) => Promise<T[]>) {
  const [offset, setOffset] = useState(0)
  const [revision, setRevision] = useState(0)
  const [items, setItems] = useState<T[]>([])
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading')
  const [error, setError] = useState('')
  useEffect(() => {
    const controller = new AbortController()
    void load(offset, controller.signal).then((result) => {
      if (!controller.signal.aborted) { setItems(result); setStatus('ready') }
    }).catch((cause) => {
      if (!controller.signal.aborted) { setError(safetyError(cause)); setStatus('error') }
    })
    return () => controller.abort()
  }, [load, offset, revision])
  function refresh() { setStatus('loading'); setError(''); setRevision((value) => value + 1) }
  function page(next: number) { setStatus('loading'); setError(''); setOffset(next) }
  return { items, status, error, offset, refresh, page }
}
