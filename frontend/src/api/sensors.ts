import { apiRequest } from './client'
import type { SensorHistory, SensorReading } from './contracts'

export const sensorsApi = {
  getHistory: (before: string, end: string, signal?: AbortSignal) => (
    apiRequest<SensorHistory>(`/api/v1/sensors/history?${new URLSearchParams({ before, end })}`, { signal })
  ),

  getLatest: (signal?: AbortSignal) => (
    apiRequest<SensorReading>('/api/v1/sensors/latest', { signal })
  ),
}
