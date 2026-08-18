import type {
  ControlKey,
  ControlSetting,
  ControlValues,
  Metric,
  MonitorRange,
  TrendSeries,
} from '../types/dashboard'

export const scheduledValues: ControlValues = {
  fan: {
    enabled: true,
    duration: 30,
    elapsedSeconds: 12 * 60,
    remainingSeconds: 18 * 60,
    nextStartSeconds: 0,
  },
  light: {
    enabled: true,
    duration: 720,
    elapsedSeconds: 282 * 60,
    remainingSeconds: 438 * 60,
    nextStartSeconds: 0,
  },
  water: {
    enabled: true,
    duration: 20,
    elapsedSeconds: 6 * 60,
    remainingSeconds: 14 * 60,
    nextStartSeconds: 0,
  },
  ph: {
    enabled: false,
    duration: 5,
    elapsedSeconds: 0,
    remainingSeconds: 0,
    nextStartSeconds: 15 * 60,
  },
}

export const controlKeys: ControlKey[] = ['fan', 'light', 'water', 'ph']

export const controlSettings: Record<ControlKey, ControlSetting> = {
  fan: {
    label: 'Fan',
    description: 'TP-Link Kasa KP303 · timed power',
    icon: 'activity',
    min: 1,
    max: 180,
    step: 1,
    durationUnit: 'min',
    restartDelaySeconds: 30 * 60,
    risk: 'low',
    tone: 'mint',
  },
  light: {
    label: 'Light',
    description: 'TP-Link Kasa KP303 · timed power',
    icon: 'sun',
    min: 1,
    max: 1440,
    step: 5,
    durationUnit: 'min',
    restartDelaySeconds: 12 * 60 * 60,
    risk: 'medium',
    tone: 'amber',
  },
  water: {
    label: 'Water Pump',
    description: 'TP-Link Kasa KP303 · timed power',
    icon: 'droplet',
    min: 1,
    max: 180,
    step: 1,
    durationUnit: 'min',
    restartDelaySeconds: 40 * 60,
    risk: 'low',
    tone: 'blue',
  },
  ph: {
    label: 'pH Dose',
    description: 'TP-Link Kasa KP303 · timed power',
    icon: 'droplet',
    min: 1,
    max: 60,
    step: 1,
    durationUnit: 'sec',
    restartDelaySeconds: 15 * 60,
    risk: 'high',
    tone: 'violet',
  },
}

export const metrics: Metric[] = [
  { label: 'Temperature', value: '24.6°C', note: 'Target 22–26°C', icon: 'temperature', tone: 'amber' },
  { label: 'Humidity', value: '68%', note: 'Target 60–75%', icon: 'droplet', tone: 'blue' },
  { label: 'Water pH', value: '6.3', note: 'Target 5.8–6.5', icon: 'activity', tone: 'violet' },
  { label: 'Nutrient EC', value: '2.7', note: 'Above safe max 2.4', icon: 'trend', tone: 'mint', alert: true },
]

export const monitorRanges: MonitorRange[] = ['24H', '7D', '30D']

export const monitorLabels: Record<MonitorRange, string[]> = {
  '24H': ['12 AM', '6 AM', '12 PM', '6 PM', 'Now'],
  '7D': ['Thu', 'Sat', 'Mon', 'Wed', 'Today'],
  '30D': ['1 Jul', '8 Jul', '15 Jul', '22 Jul', 'Today'],
}

export const selectedSnapshot: Record<MonitorRange, string> = {
  '24H': 'Today · 10:30 AM',
  '7D': 'Tuesday · 10:30 AM',
  '30D': '23 July · 10:30 AM',
}

export const trendSeries: TrendSeries[] = [
  {
    label: 'Temperature',
    value: '24.6°C',
    target: '22–26°C',
    tone: 'temperature',
    path: 'M0 25 C60 28 110 21 165 23 S255 15 320 18 S400 12 456 17 S535 13 600 15',
    pointY: 17,
  },
  {
    label: 'Humidity',
    value: '68%',
    target: '60–75%',
    tone: 'humidity',
    path: 'M0 18 C65 16 115 20 170 18 S260 24 325 21 S405 25 456 22 S535 24 600 20',
    pointY: 22,
  },
  {
    label: 'Fan',
    value: 'On',
    target: '30 min cycle',
    tone: 'fan',
    path: 'M0 24 C75 24 110 22 175 23 S265 20 330 21 S405 23 456 22 S535 20 600 21',
    pointY: 22,
  },
  {
    label: 'Light',
    value: 'On',
    target: '12 h/day',
    tone: 'light',
    path: 'M0 12 C80 12 120 11 190 12 S280 11 350 12 C405 12 430 17 456 18 S530 18 600 17',
    pointY: 18,
  },
  {
    label: 'pH',
    value: '6.3',
    target: '5.8–6.5',
    tone: 'ph',
    path: 'M0 22 C70 20 115 23 180 21 S270 22 335 20 S410 23 456 21 S535 22 600 20',
    pointY: 21,
  },
  {
    label: 'EC',
    value: '2.7 mS/cm',
    target: '1.8–2.4',
    tone: 'ec',
    path: 'M0 24 C70 23 120 25 185 22 S285 24 350 21 C395 20 420 11 456 8 S530 10 600 13',
    pointY: 8,
    alert: true,
  },
]
