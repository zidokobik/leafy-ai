const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim() ?? ''

export const apiConfig = {
  baseUrl: configuredBaseUrl.replace(/\/$/, ''),
  enabled: configuredBaseUrl.length > 0,
  requestTimeoutMs: Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 8000),
  monitoringPollMs: Number(import.meta.env.VITE_MONITORING_POLL_MS ?? 5000),
  historyPollMs: Number(import.meta.env.VITE_HISTORY_POLL_MS ?? 1800000),
}
