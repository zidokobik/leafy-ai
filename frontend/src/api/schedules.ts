import { apiRequest } from './client'
import type { AgentScheduledJob, AgentScheduledJobWrite } from './contracts'

export const schedulesApi = {
  list: (signal?: AbortSignal) => (
    apiRequest<AgentScheduledJob[]>('/api/v1/schedules', { signal })
  ),

  create: (job: AgentScheduledJobWrite) => (
    apiRequest<AgentScheduledJob>('/api/v1/schedules', {
      method: 'POST',
      body: job,
    })
  ),

  update: (jobId: string, update: AgentScheduledJobWrite) => (
    apiRequest<AgentScheduledJob>(`/api/v1/schedules/${jobId}`, {
      method: 'PATCH',
      body: update,
    })
  ),

  remove: (jobId: string) => (
    apiRequest<void>(`/api/v1/schedules/${jobId}`, { method: 'DELETE' })
  ),
}