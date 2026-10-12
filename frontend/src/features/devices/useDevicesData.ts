import { useCallback, useEffect, useState } from 'react'
import { devicesApi, type FarmDevice, type Powerboard, type PowerboardState } from '../../api/devices'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  powerboards: Powerboard[]
  devices: FarmDevice[]
  error: string
}

type StatesSnapshot = {
  version: number
  states: Record<string, PowerboardState>
  error: string
}

/**
 * Powerboards and devices from the database, plus live outlet states read from the
 * powerboards. States load separately because an unreachable board takes seconds to time out.
 */
export function useDevicesData() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [version, setVersion] = useState(0)
  const [statesSnapshot, setStatesSnapshot] = useState<StatesSnapshot | null>(null)
  const [statesVersion, setStatesVersion] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const [powerboards, devices] = await Promise.all([
          devicesApi.powerboards(controller.signal),
          devicesApi.list(controller.signal),
        ])
        if (controller.signal.aborted) return
        setSnapshot({ powerboards, devices, error: '' })
      } catch {
        if (controller.signal.aborted) return
        setSnapshot((previous) => ({
          powerboards: previous?.powerboards ?? [],
          devices: previous?.devices ?? [],
          error: 'Unable to load devices.',
        }))
      }
    }

    void load()
    return () => controller.abort()
  }, [version])

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const states = await devicesApi.powerboardStates(controller.signal)
        if (controller.signal.aborted) return
        setStatesSnapshot({
          version: statesVersion,
          states: Object.fromEntries(states.map((state) => [state.powerboardId, state])),
          error: '',
        })
      } catch {
        if (controller.signal.aborted) return
        setStatesSnapshot((previous) => ({
          version: statesVersion,
          states: previous?.states ?? {},
          error: 'Unable to read the powerboards.',
        }))
      }
    }

    void load()
    return () => controller.abort()
  }, [statesVersion])

  const refresh = useCallback(() => {
    setVersion((current) => current + 1)
    setStatesVersion((current) => current + 1)
  }, [])
  const refreshStates = useCallback(() => setStatesVersion((current) => current + 1), [])

  /** Apply an outlet state the server has just confirmed, without re-reading every powerboard. */
  const setOutletState = useCallback((powerboardId: string, outletNum: number, on: boolean) => {
    setStatesSnapshot((previous) => {
      const outlets = previous?.states[powerboardId]?.outlets
      if (!previous || !outlets) return previous
      const updated = outlets.map((value, index) => (index === outletNum - 1 ? on : value))
      return {
        ...previous,
        states: { ...previous.states, [powerboardId]: { ...previous.states[powerboardId], outlets: updated } },
      }
    })
  }, [])

  const currentStates = statesSnapshot && statesSnapshot.version === statesVersion ? statesSnapshot : null
  const status: Status = snapshot === null ? 'loading' : snapshot.error ? 'error' : 'ready'
  const statesStatus: Status = currentStates === null ? 'loading' : currentStates.error ? 'error' : 'ready'

  return {
    powerboards: snapshot?.powerboards ?? [],
    devices: snapshot?.devices ?? [],
    status,
    error: snapshot?.error ?? '',
    // The previous states stay visible while a refresh is in flight.
    states: statesSnapshot?.states ?? {},
    statesStatus,
    statesError: currentStates?.error ?? '',
    refresh,
    refreshStates,
    setOutletState,
  }
}
