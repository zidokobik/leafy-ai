import type { SensorReading } from '../../api/contracts'

export type SensorMetricKey = Exclude<keyof SensorReading, 'timestamp'>

export type SensorMetric = {
  key: SensorMetricKey
  label: string
  unit: string
  color: string
  decimals: number
  /** Smallest axis span to show, so a steady reading reads as flat instead of as noise. */
  minSpan: number
  /** Range the sensor can physically report. The axis never extends past it. */
  limits: [number, number]
}

export const sensorMetrics: SensorMetric[] = [
  { key: 'ambientTempC', label: 'Air temperature', unit: '°C', color: '#d98f3d', decimals: 1, minSpan: 6, limits: [-10, 60] },
  { key: 'humidityPct', label: 'Humidity', unit: '%', color: '#2f9bb0', decimals: 0, minSpan: 20, limits: [0, 100] },
  { key: 'waterTempC', label: 'Water temperature', unit: '°C', color: '#3f86c4', decimals: 1, minSpan: 6, limits: [0, 45] },
  { key: 'waterPh', label: 'Water pH', unit: '', color: '#7d6ad0', decimals: 2, minSpan: 1, limits: [0, 14] },
  { key: 'ecUsCm', label: 'Nutrient EC', unit: ' µS/cm', color: '#3f9d7c', decimals: 0, minSpan: 600, limits: [0, 6000] },
  { key: 'reservoirLevelCm', label: 'Reservoir level', unit: ' cm', color: '#a3763f', decimals: 1, minSpan: 10, limits: [0, 100] },
]

export function formatMetricValue(metric: SensorMetric, value: number | null | undefined) {
  return value === null || value === undefined ? '—' : `${value.toFixed(metric.decimals)}${metric.unit}`
}

/** Rounds `range / 4` to the nearest 1, 2 or 5 times a power of ten, so ticks land on round numbers. */
function niceStep(range: number) {
  const magnitude = 10 ** Math.floor(Math.log10(range / 4))
  const normalized = range / 4 / magnitude
  const multiplier = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10
  return multiplier * magnitude
}

export type SensorAxis = {
  domain: [number, number]
  ticks: number[]
  decimals: number
}

/**
 * Builds a y axis that keeps small fluctuations looking small: it covers at least
 * `metric.minSpan`, stays inside `metric.limits`, and ends on round tick values.
 */
export function buildAxis(metric: SensorMetric, values: number[]): SensorAxis {
  const [limitLow, limitHigh] = metric.limits
  const lowest = Math.min(...values)
  const highest = Math.max(...values)
  const middle = (lowest + highest) / 2
  const half = Math.max(highest - lowest, metric.minSpan) * 0.6

  let low = middle - half
  let high = middle + half
  if (low < limitLow) {
    high = Math.min(limitHigh, high + (limitLow - low))
    low = limitLow
  }
  if (high > limitHigh) {
    low = Math.max(limitLow, low - (high - limitHigh))
    high = limitHigh
  }

  const step = niceStep(high - low)
  const start = Math.floor(low / step) * step
  const end = Math.ceil(high / step) * step
  const decimals = Math.max(0, Math.ceil(-Math.log10(step)))

  const ticks: number[] = []
  for (let tick = start; tick <= end + step / 2; tick += step) {
    ticks.push(Number(tick.toFixed(decimals)))
  }

  return { domain: [start, end], ticks, decimals }
}
