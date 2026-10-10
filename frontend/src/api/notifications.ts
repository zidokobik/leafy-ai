import { apiRequest } from './client'

export type EmailRecipient = {
  recipientId: string
  email: string
  label: string | null
  enabled: boolean
  createdAt: string
}

export type EmailLog = {
  emailId: string
  recipients: string[]
  subject: string
  status: 'sent' | 'failed'
  error: string | null
  scheduleId: string | null
  triggeredBy: 'agent' | 'user'
  createdAt: string
}

export const notificationsApi = {
  recipients: (signal?: AbortSignal) => apiRequest<EmailRecipient[]>('/api/v1/notifications/recipients', { signal }),
  addRecipient: (email: string, label: string | null) =>
    apiRequest<EmailRecipient>('/api/v1/notifications/recipients', { method: 'POST', body: { email, label } }),
  setRecipientEnabled: (recipientId: string, enabled: boolean) =>
    apiRequest<EmailRecipient>(`/api/v1/notifications/recipients/${recipientId}`, { method: 'PATCH', body: { enabled } }),
  deleteRecipient: (recipientId: string) =>
    apiRequest<void>(`/api/v1/notifications/recipients/${recipientId}`, { method: 'DELETE' }),
  emailLogs: (signal?: AbortSignal) => apiRequest<EmailLog[]>('/api/v1/notifications/emails', { signal }),
  sendTestEmail: () => apiRequest<EmailLog>('/api/v1/notifications/emails/test', { method: 'POST' }),
}
