import { useEffect, useState } from 'react'
import { apiConfig } from '../../api/config'
import type { ApiConnectionState, EcDoseLiveData, EcDoseSettings } from '../../api/contracts'
import { ecDoseApi } from '../../api/leafyApi'

export const defaultEcDoseSettings: EcDoseSettings = {
  targetEc: 3000,
  movingAverage: 1,
  doseOnTime: 30,
  mixingGuard: 1,
  maxCycles: 10,
}

function createDemoLiveData(): EcDoseLiveData {
  return {
    movingAverageEc: 2742,
    validSamples: 58,
    totalSamples: 60,
    nextStartAt: new Date(Date.now() + 12 * 60 * 1000 + 18 * 1000).toISOString(),
    lastEvent: {
      type: 'dose_completed',
      occurredAt: new Date(Date.now() - 24 * 60 * 1000).toISOString(),
      durationSeconds: 30,
    },
    mixingGuardRemainingSeconds: 42,
    updatedAt: new Date().toISOString(),
  }
}

export function useEcDoseController() {
  const [settings, setSettings] = useState(defaultEcDoseSettings)
  const [live, setLive] = useState(createDemoLiveData)
  const [connectionState, setConnectionState] = useState<ApiConnectionState>(
    apiConfig.enabled ? 'loading' : 'demo',
  )
  const [apiError, setApiError] = useState<string | null>(null)

  useEffect(() => {
    if (!apiConfig.enabled) return

    const controller = new AbortController()

    const loadSnapshot = () => {
      ecDoseApi.getSnapshot(controller.signal)
        .then((snapshot) => {
          setSettings(snapshot.settings)
          setLive(snapshot.live)
          setConnectionState('connected')
          setApiError(null)
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          setConnectionState('error')
          setApiError(error instanceof Error ? error.message : 'Unable to load EC dosing data')
        })
    }

    loadSnapshot()
    const timer = window.setInterval(loadSnapshot, apiConfig.monitoringPollMs)

    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [])

  const saveSettings = (nextSettings: EcDoseSettings) => {
    setSettings(nextSettings)
    if (!apiConfig.enabled) return

    ecDoseApi.updateSettings(nextSettings)
      .then((snapshot) => {
        setSettings(snapshot.settings)
        setLive(snapshot.live)
        setConnectionState('connected')
        setApiError(null)
      })
      .catch((error: unknown) => {
        setConnectionState('error')
        setApiError(error instanceof Error ? error.message : 'Unable to save EC dosing settings')
      })
  }

  return {
    settings,
    live,
    connectionState,
    apiError,
    saveSettings,
    resetSettings: () => saveSettings(defaultEcDoseSettings),
  }
}
