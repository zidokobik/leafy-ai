import { useState } from 'react'
import type { SensorRange } from '../../api/contracts'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { SensorChart } from './SensorChart'
import { sensorMetrics } from './sensorMetrics'
import { useSensorData } from './useSensorData'

const ranges: { value: SensorRange; label: string }[] = [
  { value: '24h', label: '24 hours' },
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
]

const readingTime = new Intl.DateTimeFormat(undefined, {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})

export function OverviewPage() {
  const [range, setRange] = useState<SensorRange>('24h')
  const { history, latest, status, error } = useSensorData(range)

  return (
    <section className="flex flex-col gap-5">
      <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">Sensor readings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {latest
              ? `Last reading ${readingTime.format(Date.parse(latest.timestamp))}`
              : 'No readings recorded yet.'}
          </p>
        </div>
        <div className="max-w-full overflow-x-auto pb-1">
          <ToggleGroup
            type="single"
            variant="outline"
            value={range}
            onValueChange={(value) => { if (value) setRange(value as SensorRange) }}
            aria-label="Sensor time range"
          >
            {ranges.map(({ value, label }) => (
              <ToggleGroupItem
                key={value}
                value={value}
                aria-label={label}
              >
                {label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
      </header>

      {status === 'error' && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      {status === 'loading' && !history && (
        <div className="grid min-w-0 gap-5">
          {sensorMetrics.slice(0, 3).map((metric) => (
            <Card key={metric.key}>
              <CardHeader>
                <Skeleton className="h-4 w-40" />
              </CardHeader>
              <CardContent>
                <Skeleton className="h-72 w-full" />
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {history && (
        <div className="grid gap-5">
          {sensorMetrics.map((metric) => (
            <SensorChart
              key={metric.key}
              metric={metric}
              readings={history.readings}
              range={range}
              current={latest?.[metric.key] ?? null}
            />
          ))}
        </div>
      )}
    </section>
  )
}
