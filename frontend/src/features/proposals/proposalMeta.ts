import type { DeviceProposal, ProposalStatus } from '../../api/proposals'

type BadgeVariant = 'default' | 'secondary' | 'destructive' | 'outline'

export const openStatuses: ProposalStatus[] = ['pending', 'running']

export const proposalStatusMeta: Record<ProposalStatus, { label: string, variant: BadgeVariant }> = {
  pending: { label: 'Awaiting review', variant: 'outline' },
  running: { label: 'Running', variant: 'default' },
  completed: { label: 'Completed', variant: 'secondary' },
  stopped: { label: 'Stopped early', variant: 'secondary' },
  rejected: { label: 'Rejected', variant: 'secondary' },
  expired: { label: 'Expired', variant: 'secondary' },
  failed: { label: 'Failed', variant: 'destructive' },
}

export const proposalTime = new Intl.DateTimeFormat(undefined, {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})

/** A pending proposal past its review deadline; the server marks it expired on its next read. */
export function isExpired(proposal: DeviceProposal, now: number) {
  return proposal.status === 'pending' && Date.parse(proposal.expiresAt) <= now
}

export function formatDuration(totalSeconds: number) {
  const seconds = Math.max(0, Math.round(totalSeconds))
  const parts = []
  if (seconds >= 3600) parts.push(`${Math.floor(seconds / 3600)} h`)
  if (seconds % 3600 >= 60) parts.push(`${Math.floor((seconds % 3600) / 60)} min`)
  if (seconds % 60 || parts.length === 0) parts.push(`${seconds % 60} s`)
  return parts.join(' ')
}

export function formatRemaining(until: string, now: number) {
  return formatDuration(Math.ceil((Date.parse(until) - now) / 1000))
}
