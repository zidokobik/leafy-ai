import { useEffect, useState } from 'react'
import { apiConfig } from '../../api/config'
import type {
  ApiConnectionState,
  MonitoringHistoryPoint,
  MonitoringLatestResponse,
} from '../../api/contracts'
import { monitoringApi } from '../../api/leafyApi'
import { selectedSnapshot, trendSeries as demoTrendSeries } from '../../data/dashboard'
import type { Metric, MonitorRange, TrendSeries } from '../../types/dashboard'

const demoLatest: MonitoringLatestResponse = {
  healthScore: 84,
  status: 'attention',
  temperatureC: 24.6,
  humidityPercent: 68,
  waterPh: 6.3,
  nutrientEcMicrosiemens: 2700,
  updatedAt: new Date().toISOString(),
}

export function toDisplayMetrics(latest: MonitoringLatestResponse): Metric[] {
  return [
    {
      label: 'Temperature',
      value: `${latest.temperatureC.toFixed(1)}°C`,
      note: 'Target 22–26°C',
      icon: 'temperature',
      tone: 'amber',
    },
    {
      label: 'Humidity',
      value: `${Math.round(latest.humidityPercent)}%`,
      note: 'Target 60–75%',
      icon: 'droplet',
      tone: 'blue',
    },
    {
      label: 'Water pH',
      value: latest.waterPh.toFixed(1),
      note: 'Target 5.8–6.5',
      icon: 'activity',
      tone: 'violet',
    },
    {
      label: 'Nutrient EC',
      value: (latest.nutrientEcMicrosiemens / 1000).toFixed(1),
      note: latest.nutrientEcMicrosiemens > 2400 ? 'Above safe max 2.4' : 'Target 1.8–2.4',
      icon: 'trend',
      tone: 'mint',
      alert: latest.nutrientEcMicrosiemens > 2400,
    },
  ]
}

export function useLatestMonitoring() {
  const [latest, setLatest] = useState(demoLatest)
  const [connectionState, setConnectionState] = useState<ApiConnectionState>(
    apiConfig.enabled ? 'loading' : 'demo',
  )

  useEffect(() => {
    if (!apiConfig.enabled) return

    const controller = new AbortController()

    const loadLatest = () => {
      monitoringApi.getLatest(controller.signal)
        .then((response) => {
          setLatest(response)
          setConnectionState('connected')
        })
        .catch(() => {
          if (!controller.signal.aborted) setConnectionState('error')
        })
    }

    loadLatest()
    const timer = window.setInterval(loadLatest, apiConfig.monitoringPollMs)

    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [])

  return { latest, metrics: toDisplayMetrics(latest), connectionState }
}

type NumericPointKey = 'temperatureC' | 'humidityPercent' | 'waterPh' | 'nutrientEcMicrosiemens'

function createPath(points: MonitoringHistoryPoint[], key: NumericPointKey) {
  const values = points.map((point) => point[key])
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = Math.max(max - min, 0.001)

  return points.map((point, index) => {
    const x = points.length === 1 ? 0 : index / (points.length - 1) * 600
    const y = 35 - (point[key] - min) / spread * 28
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

function pointY(points: MonitoringHistoryPoint[], key: NumericPointKey) {
  const values = points.map((point) => point[key])
  const min = Math.min(...values)
  const max = Math.max(...values)
  const spread = Math.max(max - min, 0.001)
  const selectedIndex = Math.round((points.length - 1) * 0.76)
  return 35 - (points[selectedIndex][key] - min) / spread * 28
}

function binaryPath(points: MonitoringHistoryPoint[], key: 'fanOn' | 'lightOn') {
  return points.map((point, index) => {
    const x = points.length === 1 ? 0 : index / (points.length - 1) * 600
    const y = point[key] ? 13 : 31
    return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y}`
  }).join(' ')
}

function toTrendSeries(points: MonitoringHistoryPoint[]): TrendSeries[] {
  const latest = points.at(-1)!
  const selectedIndex = Math.round((points.length - 1) * 0.76)

  return [
    {
      label: 'Temperature',
      value: `${latest.temperatureC.toFixed(1)}°C`,
      target: '22–26°C',
      tone: 'temperature',
      path: createPath(points, 'temperatureC'),
      pointY: pointY(points, 'temperatureC'),
    },
    {
      label: 'Humidity',
      value: `${Math.round(latest.humidityPercent)}%`,
      target: '60–75%',
      tone: 'humidity',
      path: createPath(points, 'humidityPercent'),
      pointY: pointY(points, 'humidityPercent'),
    },
    {
      label: 'Fan',
      value: latest.fanOn ? 'On' : 'Off',
      target: '30 min cycle',
      tone: 'fan',
      path: binaryPath(points, 'fanOn'),
      pointY: points[selectedIndex].fanOn ? 13 : 31,
    },
    {
      label: 'Light',
      value: latest.lightOn ? 'On' : 'Off',
      target: '12 h/day',
      tone: 'light',
      path: binaryPath(points, 'lightOn'),
      pointY: points[selectedIndex].lightOn ? 13 : 31,
    },
    {
      label: 'pH',
      value: latest.waterPh.toFixed(1),
      target: '5.8–6.5',
      tone: 'ph',
      path: createPath(points, 'waterPh'),
      pointY: pointY(points, 'waterPh'),
    },
    {
      label: 'EC',
      value: `${(latest.nutrientEcMicrosiemens / 1000).toFixed(1)} mS/cm`,
      target: '1.8–2.4',
      tone: 'ec',
      path: createPath(points, 'nutrientEcMicrosiemens'),
      pointY: pointY(points, 'nutrientEcMicrosiemens'),
      alert: latest.nutrientEcMicrosiemens > 2400,
    },
  ]
}

function formatSnapshot(timestamp: string) {
  return new Intl.DateTimeFormat('en-AU', {
    weekday: 'short',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(timestamp))
}

export function useMonitoringHistory(range: MonitorRange) {
  const [series, setSeries] = useState(demoTrendSeries)
  const [snapshot, setSnapshot] = useState(selectedSnapshot[range])
  const [connectionState, setConnectionState] = useState<ApiConnectionState>(
    apiConfig.enabled ? 'loading' : 'demo',
  )

  useEffect(() => {
    if (!apiConfig.enabled) return

    const controller = new AbortController()

    monitoringApi.getHistory(range, controller.signal)
      .then((response) => {
        if (response.points.length === 0) return
        setSeries(toTrendSeries(response.points))
        const selectedIndex = Math.round((response.points.length - 1) * 0.76)
        setSnapshot(formatSnapshot(response.points[selectedIndex].timestamp))
        setConnectionState('connected')
      })
      .catch(() => {
        if (!controller.signal.aborted) setConnectionState('error')
      })

    return () => controller.abort()
  }, [range])

  return {
    series: apiConfig.enabled ? series : demoTrendSeries,
    snapshot: apiConfig.enabled ? snapshot : selectedSnapshot[range],
    connectionState,
  }
}
