import { useEffect, useState } from 'react'
import { apiConfig } from '../../api/config'
import type { ApiConnectionState, MonitoringHistoryPoint, MonitoringLatestResponse } from '../../api/contracts'
import { monitoringApi } from '../../api/leafyApi'
import { selectedSnapshot, trendSeries as demoTrendSeries } from '../../data/dashboard'
import type { Metric, MonitorRange, TrendSeries } from '../../types/dashboard'

const demoLatest: MonitoringLatestResponse = {
  healthScore: 84, status: 'attention', temperatureC: 24.6, humidityPercent: 68,
  waterPh: 6.3, nutrientEcMicrosiemens: 2700, updatedAt: new Date().toISOString(),
}

export function toDisplayMetrics(latest: MonitoringLatestResponse): Metric[] {
  return [
    { label: 'Temperature', value: `${latest.temperatureC.toFixed(1)}°C`, note: 'Target 22–26°C', icon: 'temperature', tone: 'amber' },
    { label: 'Humidity', value: `${Math.round(latest.humidityPercent)}%`, note: 'Target 60–75%', icon: 'droplet', tone: 'blue' },
    { label: 'Water pH', value: latest.waterPh.toFixed(1), note: 'Target 5.8–6.5', icon: 'activity', tone: 'violet' },
    { label: 'Nutrient EC', value: (latest.nutrientEcMicrosiemens / 1000).toFixed(1), note: 'Latest sensor reading', icon: 'trend', tone: 'mint' },
  ]
}

export function useLatestMonitoring() {
  const [latest, setLatest] = useState(demoLatest)
  const [connectionState, setConnectionState] = useState<ApiConnectionState>(apiConfig.enabled ? 'loading' : 'demo')
  useEffect(() => {
    if (!apiConfig.enabled) return
    const controller = new AbortController()
    const load = () => monitoringApi.getLatest(controller.signal).then((response) => {
      setLatest(response); setConnectionState('connected')
    }).catch(() => { if (!controller.signal.aborted) setConnectionState('error') })
    load()
    const timer = window.setInterval(load, apiConfig.monitoringPollMs)
    return () => { controller.abort(); window.clearInterval(timer) }
  }, [])
  return { latest, metrics: toDisplayMetrics(latest), connectionState }
}

type NumericKey = 'temperatureC' | 'waterTemperatureC' | 'humidityPercent' | 'waterPh' | 'nutrientEcMicrosiemens' | 'reservoirLevelCm'

function path(points: MonitoringHistoryPoint[], key: NumericKey) {
  const values = points.map((point) => point[key])
  const min = Math.min(...values)
  const spread = Math.max(Math.max(...values) - min, 0.001)
  return points.map((point, index) => {
    const x = points.length === 1 ? 0 : index / (points.length - 1) * 600
    const y = 35 - (point[key] - min) / spread * 28
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

function pointY(points: MonitoringHistoryPoint[], key: NumericKey, selected: number) {
  const values = points.map((point) => point[key])
  const min = Math.min(...values)
  const spread = Math.max(Math.max(...values) - min, 0.001)
  return 35 - (points[selected][key] - min) / spread * 28
}

function pumpPath(points: MonitoringHistoryPoint[]) {
  return points.map((point, index) => {
    const x = points.length === 1 ? 0 : index / (points.length - 1) * 600
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${point.irrigationPumpOn ? 13 : 31}`
  }).join(' ')
}

function toTrendSeries(points: MonitoringHistoryPoint[]): TrendSeries[] {
  const latest = points.at(-1)!
  const selected = Math.round((points.length - 1) * 0.76)
  const numeric = (label: string, value: string, target: string, tone: string, key: NumericKey): TrendSeries => ({ label, value, target, tone, path: path(points, key), pointY: pointY(points, key, selected) })
  return [
    numeric('Temperature', `${latest.temperatureC.toFixed(1)}°C`, '22–26°C', 'temperature', 'temperatureC'),
    numeric('Water temperature', `${latest.waterTemperatureC.toFixed(1)}°C`, '18–24°C', 'humidity', 'waterTemperatureC'),
    numeric('Humidity', `${Math.round(latest.humidityPercent)}%`, '60–75%', 'humidity', 'humidityPercent'),
    numeric('Reservoir level', `${latest.reservoirLevelCm.toFixed(1)} cm`, 'Sensor reading', 'fan', 'reservoirLevelCm'),
    { label: 'Irrigation pump', value: latest.irrigationPumpOn ? 'On' : 'Off', target: 'Sensor state', tone: 'light', path: pumpPath(points), pointY: latest.irrigationPumpOn ? 13 : 31 },
    numeric('pH', latest.waterPh.toFixed(2), '5.8–6.5', 'ph', 'waterPh'),
    numeric('EC', `${(latest.nutrientEcMicrosiemens / 1000).toFixed(2)} mS/cm`, `${(latest.ecTargetMicrosiemens / 1000).toFixed(2)} target`, 'ec', 'nutrientEcMicrosiemens'),
  ]
}

function melbourne(timestamp: string) {
  return new Intl.DateTimeFormat('en-AU', { timeZone: 'Australia/Melbourne', weekday: 'short', hour: 'numeric', minute: '2-digit' }).format(new Date(timestamp))
}

function timeLabels(points: MonitoringHistoryPoint[]) {
  return Array.from({ length: 5 }, (_, index) => melbourne(points[Math.round((points.length - 1) * index / 4)].timestamp))
}

export function useMonitoringHistory(range: MonitorRange) {
  const [series, setSeries] = useState(demoTrendSeries)
  const [labels, setLabels] = useState<string[]>([])
  const [snapshot, setSnapshot] = useState(selectedSnapshot[range])
  const [connectionState, setConnectionState] = useState<ApiConnectionState>(apiConfig.enabled ? 'loading' : 'demo')
  useEffect(() => {
    if (!apiConfig.enabled) return
    const controller = new AbortController()
    const load = () => monitoringApi.getHistory(range, controller.signal).then((response) => {
      if (!response.points.length) { setSeries([]); setLabels([]); setConnectionState('connected'); return }
      setSeries(toTrendSeries(response.points)); setLabels(timeLabels(response.points))
      const selected = Math.round((response.points.length - 1) * 0.76)
      setSnapshot(melbourne(response.points[selected].timestamp)); setConnectionState('connected')
    }).catch(() => { if (!controller.signal.aborted) setConnectionState('error') })
    load()
    const timer = window.setInterval(load, apiConfig.historyPollMs)
    return () => { controller.abort(); window.clearInterval(timer) }
  }, [range])
  return { series: apiConfig.enabled ? series : demoTrendSeries, labels: apiConfig.enabled ? labels : undefined, snapshot: apiConfig.enabled ? snapshot : selectedSnapshot[range], connectionState }
}
