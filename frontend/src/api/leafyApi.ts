import type { AlertDecision, ControlKey, MonitorRange } from '../types/dashboard'
import { apiRequest } from './client'
import type {
  AlertDecisionRequest,
  EcDoseSettings,
  EcDoseSnapshotResponse,
  MonitoringHistoryResponse,
  MonitoringLatestResponse,
  ScheduleStateResponse,
  UpdateDeviceControlRequest,
  UpdateManualModeRequest,
  UpdateRecommendationRequest,
} from './contracts'

export const scheduleApi = {
  getState: (signal?: AbortSignal) => apiRequest<ScheduleStateResponse>('/api/v1/schedule', { signal }),

  updateDevice: (device: ControlKey, update: UpdateDeviceControlRequest) => (
    apiRequest<ScheduleStateResponse>(`/api/v1/devices/${device}`, {
      method: 'PATCH',
      body: update,
    })
  ),

  setManualMode: (enabled: boolean) => apiRequest<ScheduleStateResponse>('/api/v1/schedule/manual-mode', {
    method: 'PUT',
    body: { enabled } satisfies UpdateManualModeRequest,
  }),

  reset: () => apiRequest<ScheduleStateResponse>('/api/v1/schedule/reset', { method: 'POST' }),

  setRecommendation: (applied: boolean) => (
    apiRequest<ScheduleStateResponse>('/api/v1/schedule/recommendation', {
      method: 'PUT',
      body: { applied } satisfies UpdateRecommendationRequest,
    })
  ),
}

export const alertApi = {
  setDecision: (decision: AlertDecision) => apiRequest<void>('/api/v1/alerts/ec/decision', {
    method: 'PUT',
    body: { decision } satisfies AlertDecisionRequest,
  }),
}

export const ecDoseApi = {
  getSnapshot: (signal?: AbortSignal) => (
    apiRequest<EcDoseSnapshotResponse>('/api/v1/ec-dose', { signal })
  ),

  updateSettings: (settings: EcDoseSettings) => (
    apiRequest<EcDoseSnapshotResponse>('/api/v1/ec-dose/settings', {
      method: 'PUT',
      body: settings,
    })
  ),
}

export const monitoringApi = {
  getLatest: (signal?: AbortSignal) => (
    apiRequest<MonitoringLatestResponse>('/api/v1/monitoring/latest', { signal })
  ),

  getHistory: (range: MonitorRange, signal?: AbortSignal) => (
    apiRequest<MonitoringHistoryResponse>(`/api/v1/monitoring/history?range=${range}`, { signal })
  ),
}
