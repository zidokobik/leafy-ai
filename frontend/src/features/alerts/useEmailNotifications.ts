import { useCallback, useEffect, useState } from 'react'
import { notificationsApi, type EmailLog, type EmailRecipient } from '../../api/notifications'
import { apiConfig } from '../../api/config'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  recipients: EmailRecipient[]
  logs: EmailLog[]
  error: string
}

/** Loads the admin email recipients and the send log; polls so agent sends show up live. */
export function useEmailNotifications() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion((current) => current + 1), [])

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const [recipients, logs] = await Promise.all([
          notificationsApi.recipients(controller.signal),
          notificationsApi.emailLogs(controller.signal),
        ])
        if (controller.signal.aborted) return
        setSnapshot({ recipients, logs, error: '' })
      } catch {
        if (controller.signal.aborted) return
        setSnapshot((previous) => ({
          recipients: previous?.recipients ?? [],
          logs: previous?.logs ?? [],
          error: 'Unable to load email notifications.',
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
    recipients: snapshot?.recipients ?? [],
    logs: snapshot?.logs ?? [],
    status,
    error: snapshot?.error ?? '',
    refresh,
  }
}
