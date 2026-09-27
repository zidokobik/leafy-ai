// An empty base URL keeps requests same-origin, which the Vite dev proxy forwards to FastAPI.
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? ''

export const apiConfig = {
  baseUrl: configuredBaseUrl.replace(/\/$/, ''),
  requestTimeoutMs: Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 8000),
  sensorPollMs: Number(import.meta.env.VITE_SENSOR_POLL_MS ?? 30000),
  // Images are synced hourly on the server, so a slow refresh is enough to pick up new ones.
  cameraPollMs: Number(import.meta.env.VITE_CAMERA_POLL_MS ?? 300000),
}
