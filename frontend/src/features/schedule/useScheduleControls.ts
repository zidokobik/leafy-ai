import { useEffect, useState } from 'react'
import { apiConfig } from '../../api/config'
import { scheduleApi } from '../../api/leafyApi'
import type { ApiConnectionState, ScheduleStateResponse } from '../../api/contracts'
import { controlKeys, controlSettings, scheduledValues } from '../../data/dashboard'
import type { ControlKey } from '../../types/dashboard'

function durationInSeconds(key: ControlKey, duration: number) {
  return controlSettings[key].durationUnit === 'min' ? duration * 60 : duration
}

export function useScheduleControls() {
  const [manualMode, setManualMode] = useState(false)
  const [controls, setControls] = useState(scheduledValues)
  const [saved, setSaved] = useState(false)
  const [recommendationApplied, setRecommendationApplied] = useState(false)
  const [connectionState, setConnectionState] = useState<ApiConnectionState>(
    apiConfig.enabled ? 'loading' : 'demo',
  )
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    if (!apiConfig.enabled) return

    const controller = new AbortController()

    scheduleApi.getState(controller.signal)
      .then((state) => {
        setControls(state.controls)
        setManualMode(state.manualMode)
        setRecommendationApplied(state.recommendationApplied)
        setConnectionState('connected')
        setApiError(null)
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return
        setConnectionState('error')
        setApiError(error instanceof Error ? error.message : 'Unable to load schedule')
      })

    return () => controller.abort()
  }, [])

  const syncBackend = (request: () => Promise<ScheduleStateResponse>) => {
    if (!apiConfig.enabled) return

    request()
      .then((state) => {
        setControls(state.controls)
        setManualMode(state.manualMode)
        setRecommendationApplied(state.recommendationApplied)
        setConnectionState('connected')
        setApiError(null)
      })
      .catch((error: unknown) => {
        setConnectionState('error')
        setApiError(error instanceof Error ? error.message : 'Unable to save schedule')
      })
  }

  useEffect(() => {
    const timer = window.setInterval(() => {
      setControls((current) => {
        const next = { ...current }

        controlKeys.forEach((key) => {
          const control = current[key]

          if (control.enabled) {
            const remainingSeconds = Math.max(0, control.remainingSeconds - 1)

            next[key] = remainingSeconds === 0
              ? {
                  ...control,
                  enabled: false,
                  elapsedSeconds: 0,
                  remainingSeconds: 0,
                  nextStartSeconds: controlSettings[key].restartDelaySeconds,
                }
              : {
                  ...control,
                  elapsedSeconds: control.elapsedSeconds + 1,
                  remainingSeconds,
                }
          } else {
            const nextStartSeconds = Math.max(0, control.nextStartSeconds - 1)

            next[key] = nextStartSeconds === 0
              ? {
                  ...control,
                  enabled: true,
                  elapsedSeconds: 0,
                  remainingSeconds: durationInSeconds(key, control.duration),
                  nextStartSeconds: 0,
                }
              : {
                  ...control,
                  nextStartSeconds,
                }
          }
        })

        return next
      })
    }, 1000)

    return () => window.clearInterval(timer)
  }, [])

  const changeControlDuration = (key: ControlKey, value: number) => {
    const { min, max } = controlSettings[key]
    const clampedValue = Math.min(max, Math.max(min, value))
    const duration = Math.round(clampedValue)

    setControls((current) => ({
      ...current,
      [key]: {
        ...current[key],
        duration,
        remainingSeconds: current[key].enabled
          ? Math.max(0, durationInSeconds(key, duration) - current[key].elapsedSeconds)
          : 0,
      },
    }))
    setSaved(false)
    syncBackend(() => scheduleApi.updateDevice(key, { duration }))
  }

  const toggleControl = (key: ControlKey) => {
    const enabled = !controls[key].enabled

    setControls((current) => ({
      ...current,
      [key]: {
        ...current[key],
        enabled: !current[key].enabled,
        elapsedSeconds: 0,
        remainingSeconds: current[key].enabled
          ? 0
          : durationInSeconds(key, current[key].duration),
        nextStartSeconds: current[key].enabled
          ? controlSettings[key].restartDelaySeconds
          : 0,
      },
    }))
    setSaved(false)
    syncBackend(() => scheduleApi.updateDevice(key, { enabled }))
  }

  const resetSchedule = () => {
    setControls(scheduledValues)
    setManualMode(false)
    setSaved(false)
    syncBackend(() => scheduleApi.reset())
  }

  const toggleRecommendation = () => {
    const nextApplied = !recommendationApplied

    setRecommendationApplied(nextApplied)
    setControls((current) => ({
      ...current,
      light: nextApplied
        ? {
            ...current.light,
            duration: 690,
            remainingSeconds: current.light.enabled
              ? Math.max(0, 690 * 60 - current.light.elapsedSeconds)
              : 0,
          }
        : { ...scheduledValues.light },
    }))
    syncBackend(() => scheduleApi.setRecommendation(nextApplied))
  }

  const enableManualMode = () => {
    setManualMode(true)
    syncBackend(() => scheduleApi.setManualMode(true))
  }

  return {
    manualMode,
    controls,
    saved,
    recommendationApplied,
    connectionState,
    apiError,
    changeControlDuration,
    toggleControl,
    enableManualMode,
    resetSchedule,
    saveManualSettings: () => setSaved(true),
    toggleRecommendation,
  }
}
