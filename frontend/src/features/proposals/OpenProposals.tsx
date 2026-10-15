import { CircleAlertIcon, PlugZapIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import type { DeviceProposal } from '../../api/proposals'
import { ProposalActionButtons, ProposalConfirmDialog } from './ProposalActions'
import {
  formatDuration,
  formatRemaining,
  isExpired,
  openStatuses,
  proposalStatusMeta,
  proposalTime,
} from './proposalMeta'
import { useNow } from './useNow'
import { useProposalActions } from './useProposalActions'
import { useProposals } from './useProposals'

function timing(proposal: DeviceProposal, now: number) {
  if (proposal.status === 'running' && proposal.endsAt) {
    return `Switches off in ${formatRemaining(proposal.endsAt, now)}, at ${proposalTime.format(Date.parse(proposal.endsAt))}`
  }
  if (isExpired(proposal, now)) return 'The review deadline has passed.'
  return `Proposed ${proposalTime.format(Date.parse(proposal.createdAt))} · review within ${formatRemaining(proposal.expiresAt, now)}`
}

/** Pending and running device proposals, shown on Overview right after the active alerts. */
export function OpenProposals() {
  const { proposals, refresh } = useProposals({ statuses: openStatuses })
  const actions = useProposalActions(refresh)
  const now = useNow()

  if (proposals.length === 0 && !actions.error) return null

  return (
    <section className="flex flex-col gap-2" aria-label="Device proposals">
      {actions.error && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertDescription>{actions.error}</AlertDescription>
        </Alert>
      )}
      {proposals.map((proposal) => {
        const meta = proposalStatusMeta[proposal.status]
        return (
          <div key={proposal.id} className="flex flex-col gap-3 rounded-lg border bg-card p-3 sm:flex-row sm:items-start">
            <PlugZapIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <p className="font-medium">
                  Switch on {proposal.deviceName} for {formatDuration(proposal.durationSeconds)}
                </p>
                <Badge variant={meta.variant}>{meta.label}</Badge>
                {proposal.scheduleId && <Badge variant="outline">Scheduled run</Badge>}
              </div>
              <p className="mt-1 text-sm text-muted-foreground">{proposal.reason}</p>
              <p className="mt-1 text-xs text-muted-foreground">{timing(proposal, now)}</p>
            </div>
            <div className="flex shrink-0 gap-2">
              <ProposalActionButtons proposal={proposal} now={now} busy={actions.busy} onAction={actions.request} />
            </div>
          </div>
        )
      })}
      <ProposalConfirmDialog
        confirmation={actions.confirmation}
        open={actions.confirmOpen}
        busy={actions.busy}
        onConfirm={actions.confirm}
        onCancel={actions.cancel}
      />
    </section>
  )
}
