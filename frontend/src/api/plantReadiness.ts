import { apiRequest } from './client'
import { apiConfig } from './config'
import type { PlantReadiness } from './contracts'

export const plantReadinessApi = {
  /** `asOf` is a farm local time such as `2026-10-02T18:01`; omit it for the newest frames. */
  get: (asOf: string | null, signal?: AbortSignal) => {
    const query = asOf ? `?${new URLSearchParams({ asOf })}` : ''
    return apiRequest<PlantReadiness>(`/api/v1/plant-readiness${query}`, { signal })
  },
  overlayUrl: (imageId: string) => (
    `${apiConfig.baseUrl}/api/v1/plant-readiness/overlays/${encodeURIComponent(imageId)}`
  ),
}
