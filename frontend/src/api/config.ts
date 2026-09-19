// An empty base URL keeps requests same-origin, which the Vite dev proxy forwards to FastAPI.
const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? ''

export const apiConfig = {
  baseUrl: configuredBaseUrl.replace(/\/$/, ''),
  requestTimeoutMs: Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 8000),
  sensorPollMs: Number(import.meta.env.VITE_SENSOR_POLL_MS ?? 30000),
}
