import { useCallback, useEffect, useState } from 'react'
import { alertsApi, type FarmAlert } from '../../api/alerts'
import { apiConfig } from '../../api/config'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  active: FarmAlert[]
  resolved: FarmAlert[]
  error: string
}

/** Loads every active alert (including dismissed ones) plus recent resolved history for the Alerts page. */
export function useAlertsData() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion((current) => current + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const [active, resolved] = await Promise.all([
          alertsApi.list('active', controller.signal),
          alertsApi.list('resolved', controller.signal),
        ])
        if (controller.signal.aborted) return
        setSnapshot({ active, resolved, error: '' })
      } catch {
        if (controller.signal.aborted) return
        setSnapshot((previous) => ({
          active: previous?.active ?? [],
          resolved: previous?.resolved ?? [],
          error: 'Unable to load alerts.',
        }))
      }
    }

    void load()
    const timer = window.setInterval(() => void load(), apiConfig.sensorPollMs)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [version])

  const status: Status = snapshot === null ? 'loading' : snapshot.error ? 'error' : 'ready'

  return {
    active: snapshot?.active ?? [],
    resolved: snapshot?.resolved ?? [],
    status,
    error: snapshot?.error ?? '',
    refresh,
  }
}
