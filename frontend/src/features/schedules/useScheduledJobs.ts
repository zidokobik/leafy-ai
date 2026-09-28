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
  const [reloadKey, setReloadKey] = useState(0)

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
  }, [reloadKey])

  // Refetch shortly after the earliest upcoming run so the scheduler's new next run is shown.
  useEffect(() => {
    const upcoming = state.jobs
      .map((job) => (job.nextRun ? new Date(job.nextRun).getTime() : NaN))
      .filter((time) => time > Date.now())
    if (upcoming.length === 0) return
    const delay = Math.min(Math.min(...upcoming) - Date.now() + 2000, 2 ** 31 - 1)
    const timer = window.setTimeout(() => setReloadKey((key) => key + 1), delay)
    return () => window.clearTimeout(timer)
  }, [state.jobs])

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
