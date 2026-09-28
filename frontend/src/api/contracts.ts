import type { UIMessage } from 'ai'

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
  nextRun: string | null
}

export type AgentScheduledJobWrite = Pick<
  AgentScheduledJob,
  'title' | 'instruction' | 'cronExpression'
>

/** The latest synced image for one camera. `imageUrl` and `capturedAt` are null until the first sync. */
export type CameraImage = {
  id: string
  label: string
  imageUrl: string | null
  capturedAt: string | null
}

/** A stored agent conversation. `source` is 'schedule' for scheduled agent runs. */
export type ChatConversationSummary = {
  id: string
  title: string
  source: 'chat' | 'schedule'
  scheduleId: string | null
  createdAt: string
  updatedAt: string
}

export type ChatConversationDetail = ChatConversationSummary & {
  messages: UIMessage[]
}
