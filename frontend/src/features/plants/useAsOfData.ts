import { useEffect, useState } from 'react'

type Status = 'loading' | 'ready' | 'error'

type Snapshot<T> = {
  asOf: string
  data: T | null
  error: string
}

type Loader<T> = (asOf: string | null, signal?: AbortSignal) => Promise<T>

/**
 * Loads `load(asOf)` whenever the farm-time `asOf` changes ('' = newest / now). No polling: the CV data is archived.
 * `load` must be a stable function (an API client method), or it reloads on every render.
 */
export function useAsOfData<T>(asOf: string, load: Loader<T>, errorMessage: string) {
  const [snapshot, setSnapshot] = useState<Snapshot<T> | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    const run = async () => {
      try {
        const data = await load(asOf || null, controller.signal)
        if (controller.signal.aborted) return
        setSnapshot({ asOf, data, error: '' })
      } catch {
        if (controller.signal.aborted) return
        setSnapshot({ asOf, data: null, error: errorMessage })
      }
    }

    void run()
    return () => controller.abort()
  }, [asOf, load, errorMessage])

  // A snapshot for another `asOf` is stale: show loading until the new one arrives.
  const current = snapshot?.asOf === asOf ? snapshot : null
  const status: Status = current === null ? 'loading' : current.error ? 'error' : 'ready'

  return {
    data: current?.data ?? null,
    status,
    error: current?.error ?? '',
  }
}
