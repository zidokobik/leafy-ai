import { apiRequest } from './client'

export type AlertSeverity = 'info' | 'warning' | 'critical'

export type FarmAlert = {
  alertId: string
  alertKey: string
  severity: AlertSeverity
  title: string
  message: string
  status: 'active' | 'resolved'
  occurrences: number
  scheduleId: string | null
  createdAt: string
  updatedAt: string
  resolvedAt: string | null
  resolvedBy: 'agent' | 'user' | null
  dismissedAt: string | null
}

export const alertsApi = {
  list: (status: 'active' | 'resolved' | 'all', signal?: AbortSignal) =>
    apiRequest<FarmAlert[]>(`/api/v1/alerts?status=${status}`, { signal }),
  dismiss: (alertId: string) => apiRequest<FarmAlert>(`/api/v1/alerts/${alertId}/dismiss`, { method: 'POST' }),
  resolve: (alertId: string) => apiRequest<FarmAlert>(`/api/v1/alerts/${alertId}/resolve`, { method: 'POST' }),
}
