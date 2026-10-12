import { CircleStopIcon, PowerIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import type { DeviceProposal } from '../../api/proposals'
import { formatDuration, isExpired, proposalTime } from './proposalMeta'
import type { ProposalAction, ProposalConfirmation } from './useProposalActions'

/** Approve and reject for a pending proposal, stop for a running one, nothing otherwise. */
export function ProposalActionButtons({ proposal, now, busy, onAction }: {
  proposal: DeviceProposal
  now: number
  busy: boolean
  onAction: (proposal: DeviceProposal, action: ProposalAction) => void
}) {
  if (proposal.status === 'running') {
    return (
      <Button size="sm" variant="destructive" disabled={busy} onClick={() => onAction(proposal, 'stop')}>
        <CircleStopIcon data-icon="inline-start" />
        Stop now
      </Button>
    )
  }
  if (proposal.status !== 'pending' || isExpired(proposal, now)) return null
  return (
    <>
      <Button size="sm" disabled={busy} onClick={() => onAction(proposal, 'approve')}>
        <PowerIcon data-icon="inline-start" />
        Approve
      </Button>
      <Button size="sm" variant="outline" disabled={busy} onClick={() => onAction(proposal, 'reject')}>
        Reject
      </Button>
    </>
  )
}

export function ProposalConfirmDialog({ confirmation, open, busy, onConfirm, onCancel }: {
  confirmation: ProposalConfirmation | null
  open: boolean
  busy: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  const proposal = confirmation?.proposal
  const approving = confirmation?.action === 'approve'
  const name = proposal?.deviceName ?? 'the device'

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!next) onCancel() }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {approving
              ? `Switch on ${name} for ${formatDuration(proposal?.durationSeconds ?? 0)}?`
              : `Switch off ${name} now?`}
          </DialogTitle>
          <DialogDescription>
            {approving
              ? 'The outlet switches on as soon as you approve and switches off by itself when the run ends.'
              : `The run was due to end ${proposal?.endsAt ? `at ${proposalTime.format(Date.parse(proposal.endsAt))}` : 'later'}.`}
          </DialogDescription>
        </DialogHeader>
        {approving && proposal && (
          <p className="max-h-48 overflow-y-auto rounded-lg border bg-muted/40 p-3 text-sm whitespace-pre-wrap">
            {proposal.reason}
          </p>
        )}
        <DialogFooter>
          <Button variant="outline" disabled={busy} onClick={onCancel}>Cancel</Button>
          <Button variant={approving ? 'default' : 'destructive'} disabled={busy} onClick={onConfirm}>
            {approving ? <PowerIcon data-icon="inline-start" /> : <CircleStopIcon data-icon="inline-start" />}
            {busy
              ? approving ? 'Switching on…' : 'Switching off…'
              : approving ? 'Approve and switch on' : 'Switch off now'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
