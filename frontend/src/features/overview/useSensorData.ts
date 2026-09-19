import { useEffect, useState } from 'react'
import { ApiError } from '../../api/client'
import { apiConfig } from '../../api/config'
import type { SensorHistory, SensorRange, SensorReading } from '../../api/contracts'
import { sensorsApi } from '../../api/sensors'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  range: SensorRange
  history: SensorHistory | null
  latest: SensorReading | null
  error: string
}

/**
 * Loads the bucketed history for `range` plus the newest raw reading, then refreshes on a timer.
 * The two are separate calls because a 7d or 30d bucket is an average, not a current value.
 */
export function useSensorData(range: SensorRange) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const [history, latest] = await Promise.all([
          sensorsApi.getHistory(range, controller.signal),
          sensorsApi.getLatest(controller.signal).catch((cause: unknown) => {
            if (cause instanceof ApiError && cause.status === 404) return null
            throw cause
          }),
        ])
        if (controller.signal.aborted) return
        setSnapshot({ range, history, latest, error: '' })
      } catch {
        if (controller.signal.aborted) return
        // Keep whatever is already on screen so a failed poll does not blank the charts.
        setSnapshot((previous) => ({
          range,
          history: previous?.range === range ? previous.history : null,
          latest: previous?.range === range ? previous.latest : null,
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
  }, [range])

  const current = snapshot?.range === range ? snapshot : null
  const status: Status = current === null ? 'loading' : current.error ? 'error' : 'ready'

  return {
    history: current?.history ?? null,
    latest: current?.latest ?? null,
    status,
    error: current?.error ?? '',
  }
}
