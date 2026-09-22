import { useEffect, useState } from 'react'
import { schedulesApi } from '../../api/schedules'
import type { AgentScheduledJob, AgentScheduledJobWrite } from '../../api/contracts'

type Status = 'loading' | 'ready' | 'error'

type ScheduleState = {
  jobs: AgentScheduledJob[]
  status: Status
  error: string
}

export function useScheduledJobs() {
  const [state, setState] = useState<ScheduleState>({
    jobs: [],
    status: 'loading',
    error: '',
  })

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const jobs = await schedulesApi.list(controller.signal)
        if (controller.signal.aborted) return
        setState({ jobs, status: 'ready', error: '' })
      } catch {
        if (controller.signal.aborted) return
        setState({ jobs: [], status: 'error', error: 'Unable to load schedules.' })
      }
    }

    void load()
    return () => controller.abort()
  }, [])

  async function create(job: AgentScheduledJobWrite) {
    const created = await schedulesApi.create(job)
    setState((current) => ({
      jobs: [created, ...current.jobs],
      status: 'ready',
      error: '',
    }))
    return created
  }

  async function update(jobId: string, update: AgentScheduledJobWrite) {
    const updated = await schedulesApi.update(jobId, update)
    setState((current) => ({
      jobs: current.jobs.map((job) => job.id === updated.id ? updated : job),
      status: 'ready',
      error: '',
    }))
    return updated
  }

  async function remove(jobId: string) {
    await schedulesApi.remove(jobId)
    setState((current) => ({
      jobs: current.jobs.filter((job) => job.id !== jobId),
      status: 'ready',
      error: '',
    }))
  }

  return { ...state, create, update, remove }
}