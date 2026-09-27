import { apiRequest } from './client'
import type { CameraImage } from './contracts'

export const cameraApi = {
  getLatest: (signal?: AbortSignal) => (
    apiRequest<CameraImage[]>('/api/v1/camera/latest', { signal })
  ),
}
