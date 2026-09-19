import { useState } from 'react'
import type { SensorRange } from '../../api/contracts'
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
    <section className="page-section">
      <header className="page-header">
        <div>
          <h1>Sensor readings</h1>
          <p>
            {latest
              ? `Last reading ${readingTime.format(Date.parse(latest.timestamp))}`
              : 'No readings recorded yet.'}
          </p>
        </div>
        <div className="range-tabs" role="group" aria-label="Sensor time range">
          {ranges.map(({ value, label }) => (
            <button
              key={value}
              type="button"
              className={range === value ? 'active' : undefined}
              aria-pressed={range === value}
              onClick={() => setRange(value)}
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      {status === 'error' && <p className="auth-error" role="alert">{error}</p>}
      {status === 'loading' && !history && <p className="page-notice" role="status">Loading sensor readings…</p>}

      {history && (
        <div className="chart-grid">
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
