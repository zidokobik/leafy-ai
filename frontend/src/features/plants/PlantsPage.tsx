import { useState } from 'react'
import { CameraOffIcon } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import type { PlantReadiness } from '../../api/contracts'
import { harvestReadinessApi } from '../../api/harvestReadiness'
import { plantReadinessApi } from '../../api/plantReadiness'
import { CameraCard } from '../overview/CameraGrid'
import { useCameraImages } from '../overview/useCameraImages'
import { CameraReadinessCard } from './CameraReadinessCard'
import { HarvestCard } from './HarvestCard'
import { LatestCameraImages } from './LatestCameraImages'
import { useAsOfData } from './useAsOfData'

// The archived CV results end on 8 Oct 2026; this frame is the worked example in the CV write-up.
const exampleAsOf = '2026-10-02T18:01'

function SectionHeading({ title, detail }: { title: string, detail: string }) {
  return (
    <div>
      <h2 className="text-lg font-medium tracking-tight">{title}</h2>
      <p className="text-sm text-muted-foreground">{detail}</p>
    </div>
  )
}

function CrowdingResults({ readiness }: { readiness: PlantReadiness }) {
  if (readiness.cameras.length === 0) {
    return (
      <Empty className="border">
        <EmptyHeader>
          <EmptyMedia variant="icon"><CameraOffIcon /></EmptyMedia>
          <EmptyTitle>No camera frames yet</EmptyTitle>
          <EmptyDescription>
            There is no CV result at or before this time. The archived results run from 22 Sep to 8 Oct 2026.
          </EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }
  return (
    <>
      <div className="grid gap-4 xl:grid-cols-2">
        {readiness.cameras.map((camera) => <CameraReadinessCard key={camera.cameraId} camera={camera} />)}
      </div>
      <Alert>
        <AlertTitle>Recommendations only: the grower confirms on site</AlertTitle>
        <AlertDescription>{readiness.limitations}</AlertDescription>
      </Alert>
    </>
  )
}

function LoadingCards({ count }: { count: number }) {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {Array.from({ length: count }, (_, index) => (
        <Card key={index} className="gap-0 overflow-hidden p-0">
          <Skeleton className="aspect-[704/576] w-full rounded-none" />
          <div className="flex flex-col gap-2 p-4">
            <Skeleton className="h-5 w-40" />
            <Skeleton className="h-4 w-56" />
          </div>
        </Card>
      ))}
    </div>
  )
}

export function PlantsPage() {
  // A datetime-local value ('2026-10-02T18:01') is farm local time, as the backend expects; '' = newest / now.
  const [asOf, setAsOf] = useState('')
  const crowding = useAsOfData(asOf, plantReadinessApi.get, 'Unable to load the crowding results.')
  const harvest = useAsOfData(asOf, harvestReadinessApi.get, 'Unable to load the Level 2 harvest status.')
  // One request for the latest synced images, split by level: Level 2 sits next to its harvest status.
  const images = useCameraImages()
  const level1Cameras = images.cameras.filter((camera) => camera.id.startsWith('level1_'))
  const level2Cameras = images.cameras.filter((camera) => camera.id.startsWith('level2_'))

  return (
    <section className="flex flex-col gap-5">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">Plants</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            When to expand Level 1 channels, and when Level 2 is due for harvest.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <div className="grid gap-1.5">
            <Label htmlFor="plants-as-of">As of (farm time)</Label>
            <Input
              id="plants-as-of"
              type="datetime-local"
              value={asOf}
              onChange={(event) => setAsOf(event.target.value)}
            />
          </div>
          <Button variant="outline" onClick={() => setAsOf(exampleAsOf)}>2 Oct 18:01</Button>
          <Button variant="outline" disabled={asOf === ''} onClick={() => setAsOf('')}>Now</Button>
        </div>
      </header>

      <SectionHeading
        title="Level 1 crowding"
        detail={crowding.data?.summary ?? 'Camera-based crowding estimate from the archived frames.'}
      />
      {crowding.status === 'error' && (
        <Alert variant="destructive"><AlertDescription>{crowding.error}</AlertDescription></Alert>
      )}
      {crowding.status === 'loading' && <LoadingCards count={3} />}
      {crowding.status === 'ready' && crowding.data && <CrowdingResults readiness={crowding.data} />}

      <SectionHeading title="Level 2 harvest" detail="Date rule from the recorded moves, not a camera measurement." />
      {harvest.status === 'error' && (
        <Alert variant="destructive"><AlertDescription>{harvest.error}</AlertDescription></Alert>
      )}
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,24rem)]">
        {harvest.status === 'loading' && <Skeleton className="h-40 w-full" />}
        {harvest.status === 'ready' && harvest.data && <HarvestCard harvest={harvest.data} />}
        {level2Cameras.map((camera) => <CameraCard key={camera.id} camera={camera} />)}
        {images.status === 'loading' && <Skeleton className="aspect-video w-full" />}
      </div>

      <LatestCameraImages cameras={level1Cameras} status={images.status} error={images.error} />
    </section>
  )
}
