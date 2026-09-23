import { useState } from 'react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group'
import { SensorChart } from './SensorChart'
import { sensorMetrics } from './sensorMetrics'
import { useSensorData } from './useSensorData'

const readingTime = new Intl.DateTimeFormat(undefined, {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})

const presets = [
  { value: '24h', label: '24 hours', milliseconds: 24 * 60 * 60 * 1000 },
  { value: '7d', label: '7 days', milliseconds: 7 * 24 * 60 * 60 * 1000 },
  { value: '30d', label: '30 days', milliseconds: 30 * 24 * 60 * 60 * 1000 },
] as const

function toDateTimeLocal(date: Date) {
  const localDate = new Date(date.getTime() - date.getTimezoneOffset() * 60_000)
  return localDate.toISOString().slice(0, 16)
}

export function OverviewPage() {
  const [end, setEnd] = useState(() => new Date())
  const [before, setBefore] = useState(() => new Date(Date.now() - 24 * 60 * 60 * 1000))
  const [preset, setPreset] = useState<(typeof presets)[number]['value'] | ''>('24h')
  const { history, latest, status, error } = useSensorData(before, end)

  function selectPreset(value: string) {
    const selected = presets.find((item) => item.value === value)
    if (!selected) return

    const currentEnd = new Date()
    setEnd(currentEnd)
    setBefore(new Date(currentEnd.getTime() - selected.milliseconds))
    setPreset(selected.value)
  }

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
        <div className="grid w-full gap-3 sm:w-auto">
          <ToggleGroup
            type="single"
            variant="outline"
            size="sm"
            value={preset}
            onValueChange={selectPreset}
            aria-label="Sensor interval presets"
          >
            {presets.map(({ value, label }) => (
              <ToggleGroupItem key={value} value={value} aria-label={label}>
                {label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
          <div className="grid gap-3 sm:grid-cols-2">
          <div className="grid gap-1.5">
            <Label htmlFor="sensor-before">From</Label>
            <Input
              id="sensor-before"
              type="datetime-local"
              value={toDateTimeLocal(before)}
              max={toDateTimeLocal(end)}
              onChange={(event) => {
                setBefore(new Date(event.target.value))
                setPreset('')
              }}
            />
          </div>
          <div className="grid gap-1.5">
            <Label htmlFor="sensor-end">To</Label>
            <Input
              id="sensor-end"
              type="datetime-local"
              value={toDateTimeLocal(end)}
              min={toDateTimeLocal(before)}
              onChange={(event) => {
                setEnd(new Date(event.target.value))
                setPreset('')
              }}
            />
          </div>
          </div>
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
              before={history.before}
              end={history.end}
              current={latest?.[metric.key] ?? null}
            />
          ))}
        </div>
      )}
    </section>
  )
}
