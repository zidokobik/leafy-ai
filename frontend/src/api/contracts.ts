/** A sensor sample. Every measurement is nullable because a reading can be missing a field. */
export type SensorReading = {
  timestamp: string
  waterPh: number | null
  ecUsCm: number | null
  waterTempC: number | null
  ambientTempC: number | null
  humidityPct: number | null
  reservoirLevelCm: number | null
}

export type SensorHistory = {
  before: string
  end: string
  bucketSeconds: number
  readings: SensorReading[]
}

export type UserProfile = {
  id: string
  email: string
  firstName: string | null
  lastName: string | null
}

export type AgentScheduledJob = {
  id: string
  title: string
  instruction: string
  cronExpression: string
  createdAt: string
}

export type AgentScheduledJobWrite = Pick<
  AgentScheduledJob,
  'title' | 'instruction' | 'cronExpression'
>
