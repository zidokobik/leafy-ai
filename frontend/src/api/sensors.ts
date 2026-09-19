import { apiRequest } from './client'
import type { SensorHistory, SensorRange, SensorReading } from './contracts'

export const sensorsApi = {
  getHistory: (range: SensorRange, signal?: AbortSignal) => (
    apiRequest<SensorHistory>(`/api/v1/sensors/history?range=${range}`, { signal })
  ),

  getLatest: (signal?: AbortSignal) => (
    apiRequest<SensorReading>('/api/v1/sensors/latest', { signal })
  ),
}
