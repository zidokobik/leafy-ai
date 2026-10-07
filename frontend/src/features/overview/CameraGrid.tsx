import { ImageOffIcon } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { CameraImage } from '../../api/contracts'
import { useCameraImages } from './useCameraImages'

const capturedTime = new Intl.DateTimeFormat(undefined, {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})

function CameraCard({ camera }: { camera: CameraImage }) {
  return (
    <Card className="gap-0 overflow-hidden p-0">
      {camera.imageUrl ? (
        <img
          src={camera.imageUrl}
          alt={`Latest image from ${camera.label}`}
          loading="lazy"
          className="aspect-video w-full object-cover"
        />
      ) : (
        <div className="flex aspect-video w-full flex-col items-center justify-center gap-1.5 bg-muted text-muted-foreground">
          <ImageOffIcon className="size-5" />
          <span className="text-xs">No image synced yet</span>
        </div>
      )}
      <div className="flex items-baseline justify-between gap-2 p-3">
        <span className="truncate text-sm font-medium">{camera.label}</span>
        {camera.capturedAt && (
          <span className="shrink-0 text-xs text-muted-foreground">
            {capturedTime.format(Date.parse(camera.capturedAt))}
          </span>
        )}
      </div>
    </Card>
  )
}

/** Latest camera images, shown after the alert pin and before the sensor charts. */
export function CameraGrid() {
  const { cameras, status, error } = useCameraImages()

  if (status === 'error' && cameras.length === 0) {
    return <p className="text-sm text-muted-foreground">{error}</p>
  }
  if (status === 'ready' && cameras.length === 0) return null

  return (
    <section className="flex flex-col gap-3" aria-label="Cameras">
      <h2 className="text-lg font-medium tracking-tight">Cameras</h2>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {status === 'loading'
          ? Array.from({ length: 4 }, (_, index) => (
              <Card key={index} className="gap-0 overflow-hidden p-0">
                <Skeleton className="aspect-video w-full rounded-none" />
                <div className="p-3">
                  <Skeleton className="h-4 w-24" />
                </div>
              </Card>
            ))
          : cameras.map((camera) => <CameraCard key={camera.id} camera={camera} />)}
      </div>
    </section>
  )
}
