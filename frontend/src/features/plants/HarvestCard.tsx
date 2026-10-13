import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import type { BatchHarvest, HarvestReadiness, HarvestStatus } from '../../api/contracts'

const farmTime = new Intl.DateTimeFormat(undefined, {
  weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})

const HARVEST_DAYS = 7

const statusBadges: Record<HarvestStatus, { label: string, variant: 'default' | 'secondary' | 'outline' | 'destructive' }> = {
  harvest_due: { label: 'Harvest due', variant: 'destructive' },
  harvest_tomorrow: { label: 'Due tomorrow', variant: 'default' },
  growing: { label: 'Growing', variant: 'secondary' },
  harvested: { label: 'Harvested', variant: 'outline' },
}

function BatchRow({ batch }: { batch: BatchHarvest }) {
  const badge = statusBadges[batch.status]
  const progress = Math.min(batch.daysOnLevel2 / HARVEST_DAYS, 1) * 100

  return (
    <li className="flex flex-col gap-2 border-t pt-3 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm font-medium">Batch {batch.batchId}</span>
        <Badge variant={badge.variant}>{badge.label}</Badge>
      </div>
      <p className="text-sm">{batch.message}</p>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-muted"
        role="progressbar"
        aria-label={`Day ${batch.daysOnLevel2} of ${HARVEST_DAYS} on Level 2`}
        aria-valuenow={batch.daysOnLevel2}
        aria-valuemin={0}
        aria-valuemax={HARVEST_DAYS}
      >
        <div className="h-full bg-primary" style={{ width: `${progress}%` }} />
      </div>
      <dl className="grid gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-3">
        <div><dt className="inline">Moved up: </dt><dd className="inline">{farmTime.format(new Date(batch.movedAt))}</dd></div>
        <div><dt className="inline">Due: </dt><dd className="inline">{farmTime.format(new Date(batch.dueAt))}</dd></div>
        <div>
          <dt className="inline">On Level 2: </dt>
          <dd className="inline">
            {batch.daysOnLevel2} days
            {batch.harvestedAt && ` (harvested ${farmTime.format(new Date(batch.harvestedAt))})`}
          </dd>
        </div>
      </dl>
      {batch.note && <p className="text-xs text-muted-foreground">{batch.note}</p>}
    </li>
  )
}

/** Level 2 batches and their 7-day harvest window. */
export function HarvestCard({ harvest }: { harvest: HarvestReadiness }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{harvest.summary}</CardTitle>
        <CardDescription>
          Harvest is due {HARVEST_DAYS} days after the plants move up from Level 1. As of{' '}
          {farmTime.format(new Date(harvest.asOf))} (farm time).
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        {harvest.batches.length === 0
          ? <p className="text-sm text-muted-foreground">No batch has moved to Level 2 by this time.</p>
          : <ul className="flex flex-col gap-3">{harvest.batches.map((batch) => <BatchRow key={batch.batchId} batch={batch} />)}</ul>}
        <p className="text-xs text-muted-foreground">{harvest.limitations}</p>
      </CardContent>
    </Card>
  )
}
