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

export type PlantStatus = 'empty' | 'growing' | 'candidate' | 'ready' | 'uncertain'

/** expand_channel = touching in the same channel; check_spacing = touching the next channel. */
export type GrowerAction = 'expand_channel' | 'check_spacing' | 'check_canopy'

/** One `ready` hole or canopy zone. Contacts are null when not measurable (never 0). */
export type PlantRecommendation = {
  holeId: string
  action: GrowerAction
  message: string
  row: number | null
  col: number | null
  contactAlong: number | null
  contactAcross: number | null
  confirmedFrames: number
}

/** One camera's frame. `capturedAt` is farm local time without a timezone. */
export type CameraReadiness = {
  cameraId: string
  period: string
  capturedAt: string
  imageId: string
  statusCounts: Partial<Record<PlantStatus, number>>
  recommendations: PlantRecommendation[]
}

export type HarvestStatus = 'growing' | 'harvest_tomorrow' | 'harvest_due' | 'harvested'

/** A batch moved from Level 1 to Level 2; times are farm local time without a timezone. */
export type BatchHarvest = {
  batchId: number
  movedAt: string
  dueAt: string
  harvestedAt: string | null
  daysOnLevel2: number
  status: HarvestStatus
  message: string
  note: string
}

export type HarvestReadiness = {
  asOf: string
  batches: BatchHarvest[]
  summary: string
  limitations: string
}

export type PlantReadiness = {
  level: number
  asOf: string | null
  modelVersion: string | null
  cameras: CameraReadiness[]
  summary: string
  limitations: string
}
