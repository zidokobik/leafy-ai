import type { AlertDecision, ControlValues, MonitorRange } from '../types/dashboard'

export type ApiConnectionState = 'demo' | 'loading' | 'connected' | 'error'

export type ScheduleStateResponse = {
  manualMode: boolean
  recommendationApplied: boolean
  controls: ControlValues
  updatedAt: string
}

export type UpdateDeviceControlRequest = {
  enabled?: boolean
  duration?: number
}

export type UpdateManualModeRequest = {
  enabled: boolean
}

export type UpdateRecommendationRequest = {
  applied: boolean
}

export type AlertDecisionRequest = {
  decision: AlertDecision
}

export type EcDoseSettings = {
  targetEc: number
  movingAverage: number
  doseOnTime: number
  mixingGuard: number
  maxCycles: number
}

export type EcDoseLastEvent = {
  type: 'dose_completed' | 'dose_blocked' | 'settings_updated' | 'none'
  occurredAt: string | null
  durationSeconds: number | null
}

export type EcDoseLiveData = {
  movingAverageEc: number
  validSamples: number
  totalSamples: number
  nextStartAt: string | null
  lastEvent: EcDoseLastEvent
  mixingGuardRemainingSeconds: number
  updatedAt: string
}

export type EcDoseSnapshotResponse = {
  settings: EcDoseSettings
  live: EcDoseLiveData
}

export type MonitoringLatestResponse = {
  healthScore: number
  status: 'healthy' | 'attention'
  temperatureC: number
  humidityPercent: number
  waterPh: number
  nutrientEcMicrosiemens: number
  updatedAt: string
}

export type MonitoringHistoryPoint = {
  timestamp: string
  temperatureC: number
  humidityPercent: number
  waterPh: number
  nutrientEcMicrosiemens: number
  fanOn: boolean
  lightOn: boolean
}

export type MonitoringHistoryResponse = {
  range: MonitorRange
  points: MonitoringHistoryPoint[]
}
