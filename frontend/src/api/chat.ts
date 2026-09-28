import { apiRequest } from './client'
import type { ChatConversationDetail, ChatConversationSummary } from './contracts'

export const chatApi = {
  listConversations: (signal?: AbortSignal) => (
    apiRequest<ChatConversationSummary[]>('/api/v1/chat/conversations', { signal })
  ),

  getConversation: (conversationId: string, signal?: AbortSignal) => (
    apiRequest<ChatConversationDetail>(`/api/v1/chat/conversations/${conversationId}`, { signal })
  ),

  removeConversation: (conversationId: string) => (
    apiRequest<void>(`/api/v1/chat/conversations/${conversationId}`, { method: 'DELETE' })
  ),
}
