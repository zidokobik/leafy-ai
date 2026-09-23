// Display-only fixtures: never sent to the API or used to execute an agent.
export type MockRunStatus = 'never_run' | 'running' | 'succeeded' | 'failed'

export function mockScheduleRun(status: MockRunStatus, referenceTime: number) {
  const iso = (offset: number) => new Date(referenceTime + offset).toISOString()
  return {
    lastStatus: status,
    lastStartedAt: status === 'never_run' ? null : iso(status === 'running' ? -90000 : -3600000),
    lastCompletedAt: status === 'never_run' ? null : iso(status === 'running' ? -3600000 : -3540000),
    lastError: status === 'failed' ? 'Demo: the scheduled agent run could not be completed.' : null,
    nextRunAt: iso(7200000),
  }
}
