import { apiRequest } from './client'

export type SafetyRuleWrite = {
  deviceId: string
  actionType: 'run_for_duration'
  maxDurationSeconds: number
  cooldownSeconds: number
  enabled: boolean
}
export type SafetyRule = SafetyRuleWrite & { ruleId: string }
export type CommandRequest = {
  requestId: string
  deviceId: string
  decisionId: string | null
  durationSeconds: number
  reason: string
  status: string
  createdAt: string
  expiresAt: string
  startedAt: string | null
  reviewedAt: string | null
  reviewedBy: string | null
  resultMessage: string | null
}
export const safetyApi = {
  commands: (offset: number, signal?: AbortSignal) => apiRequest<CommandRequest[]>(`/api/v1/command-requests?limit=20&offset=${offset}`, { signal }),
  rules: (offset: number, signal?: AbortSignal) => apiRequest<SafetyRule[]>(`/api/v1/safety-rules?limit=20&offset=${offset}`, { signal }),
  review: (id: string, action: 'approve' | 'reject') => apiRequest<CommandRequest>(`/api/v1/command-requests/${id}/review`, { method: 'POST', body: { action } }),
  saveRule: (body: SafetyRuleWrite, id?: string) => apiRequest<SafetyRule>(`/api/v1/safety-rules${id ? `/${id}` : ''}`, { method: id ? 'PUT' : 'POST', body }),
  deleteRule: (id: string) => apiRequest<void>(`/api/v1/safety-rules/${id}`, { method: 'DELETE' }),
}
