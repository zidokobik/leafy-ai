import { apiRequest } from './client'
import type { HarvestReadiness } from './contracts'

export const harvestReadinessApi = {
  /** `asOf` is a farm local time such as `2026-10-06T12:00`; omit it for now. */
  get: (asOf: string | null, signal?: AbortSignal) => {
    const query = asOf ? `?${new URLSearchParams({ asOf })}` : ''
    return apiRequest<HarvestReadiness>(`/api/v1/harvest-readiness${query}`, { signal })
  },
}
