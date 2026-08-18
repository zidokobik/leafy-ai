import type { IconName } from '../components/Icon'

export type AlertDecision = 'pending' | 'authorized' | 'rejected'

export type UserRole = 'viewer' | 'operator'

export type ControlKey = 'fan' | 'light' | 'water' | 'ph'

export type ControlValue = {
  enabled: boolean
  duration: number
  elapsedSeconds: number
  remainingSeconds: number
  nextStartSeconds: number
}

export type ControlValues = Record<ControlKey, ControlValue>

export type ControlSetting = {
  label: string
  description: string
  alert?: boolean
  icon: IconName
  min: number
  max: number
  step: number
  durationUnit: 'min' | 'sec'
  restartDelaySeconds: number
  risk: 'low' | 'medium' | 'high'
  tone: string
}

export type Metric = {
  label: string
  value: string
  note: string
  icon: IconName
  tone: string
  alert?: boolean
}

export type MonitorRange = '24H' | '7D' | '30D'

export type TrendSeries = {
  label: string
  value: string
  target: string
  tone: string
  path: string
  pointY: number
  alert?: boolean
}
