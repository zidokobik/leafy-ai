import { useEffect, useState } from 'react'
import { cameraApi } from '../../api/camera'
import { apiConfig } from '../../api/config'
import type { CameraImage } from '../../api/contracts'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  cameras: CameraImage[]
  error: string
}

/** Loads the latest synced image for every camera, refreshed on a slow timer. */
export function useCameraImages() {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)

  useEffect(() => {
    const controller = new AbortController()

    const load = async () => {
      try {
        const cameras = await cameraApi.getLatest(controller.signal)
        if (controller.signal.aborted) return
        setSnapshot({ cameras, error: '' })
      } catch {
        if (controller.signal.aborted) return
        // Keep the current images so a failed poll does not blank the grid.
        setSnapshot((previous) => ({
          cameras: previous?.cameras ?? [],
          error: 'Unable to load camera images.',
        }))
      }
    }

    void load()
    const timer = window.setInterval(() => void load(), apiConfig.cameraPollMs)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [])

  const status: Status = snapshot === null ? 'loading' : snapshot.error ? 'error' : 'ready'

  return {
    cameras: snapshot?.cameras ?? [],
    status,
    error: snapshot?.error ?? '',
  }
}
