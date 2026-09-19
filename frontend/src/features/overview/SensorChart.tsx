import { useMemo } from 'react'
import { Area, AreaChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import type { SensorRange, SensorReading } from '../../api/contracts'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
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
  const chartConfig = {
    value: {
      label: metric.label,
      color: metric.color,
    },
  } satisfies ChartConfig

  return (
    <Card className="min-w-0">
      <CardHeader>
        <CardTitle>{metric.label}</CardTitle>
        <CardDescription>Current reading</CardDescription>
        <CardAction className="text-2xl font-medium tabular-nums" style={{ color: metric.color }}>
          {formatMetricValue(metric, current)}
        </CardAction>
      </CardHeader>

      <CardContent className="min-w-0">
        {axis ? (
          <ChartContainer config={chartConfig} initialDimension={{ width: 240, height: 288 }} className="h-72 min-w-0 w-full aspect-auto">
            <AreaChart accessibilityLayer data={data} margin={{ top: 6, right: 8, bottom: 0, left: 0 }}>
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
            <ChartTooltip
              labelFormatter={(label) => {
                const timestamp = Number(label)
                return Number.isFinite(timestamp) ? tooltipTime.format(timestamp) : undefined
              }}
              content={(
                <ChartTooltipContent
                  indicator="line"
                  formatter={(value) => formatMetricValue(metric, typeof value === 'number' ? value : null)}
                />
              )}
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
          </ChartContainer>
        ) : (
          <Empty className="h-72 border">
            <EmptyHeader>
              <EmptyTitle>No data</EmptyTitle>
              <EmptyDescription>No readings are available for this sensor in the selected range.</EmptyDescription>
            </EmptyHeader>
          </Empty>
        )}
      </CardContent>
    </Card>
  )
}
