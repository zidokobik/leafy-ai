import { Badge } from '@/components/ui/badge'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { CameraImage } from '../../api/contracts'
import { CameraCard } from '../overview/CameraGrid'

type Props = {
  cameras: CameraImage[]
  status: 'loading' | 'ready' | 'error'
  error: string
}

/** Latest synced Level 1 images, shown after the CV results to make clear they are not measured yet. */
export function LatestCameraImages({ cameras, status, error }: Props) {
  return (
    <section className="flex flex-col gap-3" aria-label="Latest Level 1 camera images">
      <div className="flex flex-col gap-1">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-lg font-medium tracking-tight">Latest Level 1 camera images</h2>
          <Badge variant="outline">Not analysed yet</Badge>
        </div>
        <p className="text-sm text-muted-foreground">
          The trays were rearranged on 8 Oct 2026. The CV measures a layout only after its planting holes are mapped,
          so these frames get crowding results once new hole maps are made.
        </p>
      </div>
      {status === 'error' && cameras.length === 0 && <p className="text-sm text-muted-foreground">{error}</p>}
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {status === 'loading'
          ? Array.from({ length: 3 }, (_, index) => (
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
