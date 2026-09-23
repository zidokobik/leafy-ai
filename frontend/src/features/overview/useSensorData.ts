import { useEffect, useState } from 'react'
import { ApiError } from '../../api/client'
import { apiConfig } from '../../api/config'
import type { SensorHistory, SensorReading } from '../../api/contracts'
import { sensorsApi } from '../../api/sensors'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  before: string
  end: string
  history: SensorHistory | null
  latest: SensorReading | null
  error: string
}

/**
 * Loads the bucketed history for an interval plus the newest raw reading, then refreshes on a timer.
 * The two are separate calls because a history bucket is an average, not a current value.
 */
export function useSensorData(before: Date, end: Date) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const beforeIso = before.toISOString()
  const endIso = end.toISOString()

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const [history, latest] = await Promise.all([
          sensorsApi.getHistory(beforeIso, endIso, controller.signal),
          sensorsApi.getLatest(controller.signal).catch((cause: unknown) => {
            if (cause instanceof ApiError && cause.status === 404) return null
            throw cause
          }),
        ])
        if (controller.signal.aborted) return
        setSnapshot({ before: beforeIso, end: endIso, history, latest, error: '' })
      } catch {
        if (controller.signal.aborted) return
        // Keep whatever is already on screen so a failed poll does not blank the charts.
        setSnapshot((previous) => ({
          before: beforeIso,
          end: endIso,
          history: previous?.before === beforeIso && previous.end === endIso ? previous.history : null,
          latest: previous?.before === beforeIso && previous.end === endIso ? previous.latest : null,
          error: 'Unable to load sensor readings.',
        }))
      }
    }

    void load()
    const timer = window.setInterval(() => void load(), apiConfig.sensorPollMs)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [beforeIso, endIso])

  const current = snapshot?.before === beforeIso && snapshot.end === endIso ? snapshot : null
  const status: Status = current === null ? 'loading' : current.error ? 'error' : 'ready'

  return {
    history: current?.history ?? null,
    latest: current?.latest ?? null,
    status,
    error: current?.error ?? '',
  }
}
