import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type {
  CameraReadiness,
  GrowerAction,
  PlantRecommendation,
  PlantStatus,
} from '../../api/contracts'
import { plantReadinessApi } from '../../api/plantReadiness'

const frameTime = new Intl.DateTimeFormat(undefined, {
  weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})

// Same order as the backend: same-channel crowding first, because channel expansion fixes it.
const actionGroups: { action: GrowerAction, title: string, variant: 'default' | 'secondary' | 'outline' }[] = [
  { action: 'expand_channel', title: 'Expand this channel today', variant: 'default' },
  { action: 'check_spacing', title: 'Touching the next channel: check spacing', variant: 'secondary' },
  { action: 'check_canopy', title: 'Closed canopy area: check today', variant: 'outline' },
]

const statusOrder: PlantStatus[] = ['ready', 'candidate', 'growing', 'empty', 'uncertain']

/** "level1_camera2" -> "Level 1 · Camera 2". */
function cameraLabel(cameraId: string) {
  const match = /^level(\d+)_camera(\d+)$/.exec(cameraId)
  return match ? `Level ${match[1]} · Camera ${match[2]}` : cameraId
}

/** "L1-C2-R03-H05" -> "R03-H05"; zone "L1-C1-Z-dense_far" -> "dense_far". */
function shortHoleId(holeId: string) {
  return holeId.replace(/^L\d+-C\d+-(Z-)?/, '')
}

function formatContact(value: number | null) {
  return value === null ? 'n/a' : value.toFixed(2)
}

function HoleBadge({ item, variant }: { item: PlantRecommendation, variant: 'default' | 'secondary' | 'outline' }) {
  const detail = item.action === 'check_canopy'
    ? `${item.holeId}: canopy closed, ${item.confirmedFrames} frames`
    : `${item.holeId}: along ${formatContact(item.contactAlong)}, across ${formatContact(item.contactAcross)}, `
      + `${item.confirmedFrames} frames crowded`
  return <Badge variant={variant} title={detail}>{shortHoleId(item.holeId)}</Badge>
}

export function CameraReadinessCard({ camera }: { camera: CameraReadiness }) {
  const overlayUrl = plantReadinessApi.overlayUrl(camera.imageId)
  const counts = statusOrder.filter((status) => camera.statusCounts[status])

  return (
    <Card className="gap-0 overflow-hidden p-0">
      <a href={overlayUrl} target="_blank" rel="noreferrer" title="Open the full-size overlay">
        <img
          src={overlayUrl}
          alt={`CV overlay for ${cameraLabel(camera.cameraId)}: plant outlines, red lines where leaves touch`}
          loading="lazy"
          className="aspect-[704/576] w-full bg-muted object-contain"
        />
      </a>
      <CardHeader className="p-4">
        <CardTitle>{cameraLabel(camera.cameraId)}</CardTitle>
        <CardDescription>
          Frame {frameTime.format(new Date(camera.capturedAt))} · layout {camera.period}
        </CardDescription>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {counts.map((status) => (
            <Badge key={status} variant="outline">{camera.statusCounts[status]} {status}</Badge>
          ))}
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-4 px-4 pb-4">
        {camera.recommendations.length === 0 && (
          <p className="text-sm text-muted-foreground">Nothing to do on this camera.</p>
        )}
        {actionGroups.map(({ action, title, variant }) => {
          const items = camera.recommendations.filter((item) => item.action === action)
          if (items.length === 0) return null
          return (
            <section key={action} className="flex flex-col gap-2" aria-label={title}>
              <h3 className="text-sm font-medium">
                {title} <span className="text-muted-foreground">({items.length})</span>
              </h3>
              <div className="flex flex-wrap gap-1.5">
                {items.map((item) => <HoleBadge key={item.holeId} item={item} variant={variant} />)}
              </div>
            </section>
          )
        })}
      </CardContent>
    </Card>
  )
}
