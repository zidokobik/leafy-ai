import { apiRequest } from './client'

export type ProposalStatus = 'pending' | 'running' | 'completed' | 'stopped' | 'rejected' | 'expired' | 'failed'

export type DeviceProposal = {
  id: string
  /** Null once the device has been deleted; deviceName keeps the name it had. */
  deviceId: string | null
  deviceName: string
  durationSeconds: number
  reason: string
  status: ProposalStatus
  scheduleId: string | null
  createdAt: string
  expiresAt: string
  reviewedBy: string | null
  reviewerEmail: string | null
  reviewedAt: string | null
  startedAt: string | null
  endsAt: string | null
  finishedAt: string | null
  resultMessage: string | null
}

// Approving and stopping switch a powerboard outlet, which can take several seconds.
const hardwareTimeoutMs = 30_000

export const proposalsApi = {
  list: (
    { statuses = [], limit = 50, offset = 0 }: { statuses?: ProposalStatus[], limit?: number, offset?: number },
    signal?: AbortSignal,
  ) => {
    const query = new URLSearchParams({ limit: String(limit), offset: String(offset) })
    for (const status of statuses) query.append('status', status)
    return apiRequest<DeviceProposal[]>(`/api/v1/proposals?${query}`, { signal })
  },
  approve: (id: string) =>
    apiRequest<DeviceProposal>(`/api/v1/proposals/${id}/approve`, { method: 'POST', timeoutMs: hardwareTimeoutMs }),
  reject: (id: string) => apiRequest<DeviceProposal>(`/api/v1/proposals/${id}/reject`, { method: 'POST' }),
  stop: (id: string) =>
    apiRequest<DeviceProposal>(`/api/v1/proposals/${id}/stop`, { method: 'POST', timeoutMs: hardwareTimeoutMs }),
}
