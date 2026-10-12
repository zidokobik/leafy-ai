import { useRef, useState } from 'react'
import { errorDetail } from '../../api/client'
import { proposalsApi, type DeviceProposal } from '../../api/proposals'
import { formatDuration } from './proposalMeta'

export type ProposalAction = 'approve' | 'reject' | 'stop'

export type ProposalConfirmation = {
  proposal: DeviceProposal
  action: 'approve' | 'stop'
}

function resultNotice(proposal: DeviceProposal) {
  if (proposal.status === 'running') {
    return `${proposal.deviceName} is on for ${formatDuration(proposal.durationSeconds)} and switches off by itself.`
  }
  if (proposal.status === 'stopped') return `${proposal.deviceName} was switched off.`
  if (proposal.status === 'rejected') return `Proposal for ${proposal.deviceName} rejected.`
  return `The proposal is now ${proposal.status}.`
}

/**
 * Approve, reject and stop, one action at a time. Approving and stopping switch real
 * hardware, so they go through a confirmation first; rejecting runs straight away.
 */
export function useProposalActions(onChanged: () => void) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  // Kept after closing so the dialog does not change text while it animates out.
  const [confirmation, setConfirmation] = useState<ProposalConfirmation | null>(null)
  const [confirmOpen, setConfirmOpen] = useState(false)
  const lock = useRef(false)

  async function run(proposal: DeviceProposal, action: ProposalAction) {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setError('')
    setNotice('')
    try {
      const result = await proposalsApi[action](proposal.id)
      if (result.status === 'failed') {
        setError(`${result.deviceName} was not switched on. ${result.resultMessage ?? ''}`.trim())
      } else {
        setNotice(resultNotice(result))
      }
    } catch (cause) {
      setError(errorDetail(cause, `Unable to ${action} the proposal. Refresh and try again.`))
    } finally {
      lock.current = false
      setBusy(false)
      setConfirmOpen(false)
      onChanged()
    }
  }

  function request(proposal: DeviceProposal, action: ProposalAction) {
    if (action === 'reject') {
      void run(proposal, action)
      return
    }
    setConfirmation({ proposal, action })
    setConfirmOpen(true)
  }

  return {
    busy,
    error,
    notice,
    confirmation,
    confirmOpen,
    request,
    confirm: () => { if (confirmation) void run(confirmation.proposal, confirmation.action) },
    cancel: () => { if (!lock.current) setConfirmOpen(false) },
  }
}
