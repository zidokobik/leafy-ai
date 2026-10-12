import { apiRequest } from './client'

export type DeviceType = 'fan' | 'light' | 'irrigation_pump' | 'ec_doser' | 'ph_doser'

export type Powerboard = {
  id: string
  name: string
  host: string
}

export type PowerboardWrite = Omit<Powerboard, 'id'>

/** Live outlet states; `outlets` is null when the powerboard could not be reached. */
export type PowerboardState = {
  powerboardId: string
  outlets: boolean[] | null
  error: string | null
}

export type FarmDevice = {
  id: string
  name: string
  deviceType: DeviceType
  powerboardId: string
  /** 1-based outlet position on the powerboard. */
  outletNum: number
}

export type FarmDeviceWrite = Omit<FarmDevice, 'id'>

// Reading every powerboard can take several seconds when one is unreachable.
const hardwareTimeoutMs = 30_000

export const devicesApi = {
  powerboards: (signal?: AbortSignal) => apiRequest<Powerboard[]>('/api/v1/powerboards', { signal }),
  powerboardStates: (signal?: AbortSignal) =>
    apiRequest<PowerboardState[]>('/api/v1/powerboards/states', { signal, timeoutMs: hardwareTimeoutMs }),
  createPowerboard: (body: PowerboardWrite) =>
    apiRequest<Powerboard>('/api/v1/powerboards', { method: 'POST', body }),
  updatePowerboard: (id: string, body: PowerboardWrite) =>
    apiRequest<Powerboard>(`/api/v1/powerboards/${id}`, { method: 'PUT', body }),
  deletePowerboard: (id: string) => apiRequest<void>(`/api/v1/powerboards/${id}`, { method: 'DELETE' }),
  list: (signal?: AbortSignal) => apiRequest<FarmDevice[]>('/api/v1/devices', { signal }),
  create: (body: FarmDeviceWrite) => apiRequest<FarmDevice>('/api/v1/devices', { method: 'POST', body }),
  update: (id: string, body: FarmDeviceWrite) =>
    apiRequest<FarmDevice>(`/api/v1/devices/${id}`, { method: 'PUT', body }),
  remove: (id: string) => apiRequest<void>(`/api/v1/devices/${id}`, { method: 'DELETE' }),
  /** Switch by hand. Switching off also stops a run in progress; switching on lasts until switched off. */
  turnOn: (id: string) =>
    apiRequest<void>(`/api/v1/devices/${id}/turn-on`, { method: 'POST', timeoutMs: hardwareTimeoutMs }),
  turnOff: (id: string) =>
    apiRequest<void>(`/api/v1/devices/${id}/turn-off`, { method: 'POST', timeoutMs: hardwareTimeoutMs }),
}
