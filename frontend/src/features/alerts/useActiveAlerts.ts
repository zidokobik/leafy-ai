import { useCallback, useEffect, useState } from 'react'
import { alertsApi, type FarmAlert } from '../../api/alerts'
import { apiConfig } from '../../api/config'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  alerts: FarmAlert[]
  error: string
}

/** Polls the alerts pinned on Overview: active and not dismissed. Dismissing hides, never resolves. */
export function useActiveAlerts() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion((current) => current + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const active = await alertsApi.list('active', controller.signal)
        if (controller.signal.aborted) return
        setSnapshot({ alerts: active.filter((alert) => alert.dismissedAt === null), error: '' })
      } catch {
        if (controller.signal.aborted) return
        // Keep the alerts already on screen so a failed poll does not hide them.
        setSnapshot((previous) => ({ alerts: previous?.alerts ?? [], error: 'Unable to load alerts.' }))
      }
    }

    void load()
    const timer = window.setInterval(() => void load(), apiConfig.sensorPollMs)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [version])

  const dismiss = useCallback(async (alertId: string) => {
    setSnapshot((previous) => (
      previous ? { ...previous, alerts: previous.alerts.filter((alert) => alert.alertId !== alertId) } : previous
    ))
    try {
      await alertsApi.dismiss(alertId)
    } catch {
      // Ignored: the re-sync below makes the alert reappear if dismissing failed.
    } finally {
      refresh()
    }
  }, [refresh])

  const status: Status = snapshot === null ? 'loading' : snapshot.error ? 'error' : 'ready'

  return {
    alerts: snapshot?.alerts ?? [],
    status,
    dismiss,
  }
}
