import { useMemo } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { SensorRange, SensorReading } from '../../api/contracts'
import { buildAxis, formatMetricValue, type SensorMetric } from './sensorMetrics'

const axisTimeFormats: Record<SensorRange, Intl.DateTimeFormatOptions> = {
  '24h': { hour: '2-digit', minute: '2-digit' },
  '7d': { weekday: 'short', hour: '2-digit' },
  '30d': { day: 'numeric', month: 'short' },
}

const tooltipTimeFormat: Intl.DateTimeFormatOptions = {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
}

type SensorChartProps = {
  metric: SensorMetric
  readings: SensorReading[]
  range: SensorRange
  current: number | null
}

export function SensorChart({ metric, readings, range, current }: SensorChartProps) {
  // Timestamps are rendered in the browser's own timezone.
  const axisTime = useMemo(() => new Intl.DateTimeFormat(undefined, axisTimeFormats[range]), [range])
  const tooltipTime = useMemo(() => new Intl.DateTimeFormat(undefined, tooltipTimeFormat), [])

  const data = useMemo(
    () => readings.map((reading) => ({ time: Date.parse(reading.timestamp), value: reading[metric.key] })),
    [readings, metric.key],
  )
  const axis = useMemo(() => {
    const values = data.map((point) => point.value).filter((value) => value !== null)
    return values.length ? buildAxis(metric, values) : null
  }, [data, metric])
  const gradientId = `sensor-fill-${metric.key}`
  return (
    <article className="chart-card">
      <header className="chart-card-head">
        <h3>{metric.label}</h3>
        <strong style={{ color: metric.color }}>{formatMetricValue(metric, current)}</strong>
      </header>

      {axis ? (
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={metric.color} stopOpacity={0.3} />
                <stop offset="100%" stopColor={metric.color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#e1e5dc" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="time"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(value: number) => axisTime.format(value)}
              tick={{ fill: '#7c887f', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: '#e1e5dc' }}
              minTickGap={28}
            />
            <YAxis
              width={58}
              domain={axis.domain}
              ticks={axis.ticks}
              tickFormatter={(value: number) => value.toFixed(axis.decimals)}
              tick={{ fill: '#7c887f', fontSize: 11 }}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip
              labelFormatter={(label) => tooltipTime.format(Number(label))}
              formatter={(value) => formatMetricValue(metric, typeof value === 'number' ? value : null)}
              contentStyle={{
                border: '1px solid #dfe3da', borderRadius: 10,
                background: '#fffdf7', fontSize: 12, boxShadow: '0 10px 24px #273d3518',
              }}
            />
            <Area
              type="monotone"
              dataKey="value"
              name={metric.label}
              stroke={metric.color}
              strokeWidth={2}
              fill={`url(#${gradientId})`}
              connectNulls
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <p className="chart-empty">No data</p>
      )}
    </article>
  )
}
