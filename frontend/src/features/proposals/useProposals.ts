import { useCallback, useEffect, useMemo, useState } from 'react'
import { apiConfig } from '../../api/config'
import { proposalsApi, type DeviceProposal, type ProposalStatus } from '../../api/proposals'

type Status = 'loading' | 'ready' | 'error'

type Snapshot = {
  key: string
  proposals: DeviceProposal[]
  error: string
}

type Options = {
  statuses?: ProposalStatus[]
  limit?: number
  offset?: number
}

/** Polls device proposals, and re-reads right after the next run ends or review deadline passes. */
export function useProposals({ statuses = [], limit = 50, offset = 0 }: Options = {}) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [version, setVersion] = useState(0)
  const refresh = useCallback(() => setVersion((current) => current + 1), [])
  const statusKey = statuses.join(',')
  const key = `${statusKey}|${limit}|${offset}`

  useEffect(() => {
    const controller = new AbortController()
    const filter = statusKey ? (statusKey.split(',') as ProposalStatus[]) : []

    const load = async () => {
      try {
        const proposals = await proposalsApi.list({ statuses: filter, limit, offset }, controller.signal)
        if (controller.signal.aborted) return
        setSnapshot({ key, proposals, error: '' })
      } catch {
        if (controller.signal.aborted) return
        // Keep what is on screen so a failed poll does not hide proposals awaiting review.
        setSnapshot((previous) => ({
          key,
          proposals: previous?.key === key ? previous.proposals : [],
          error: 'Unable to load device proposals.',
        }))
      }
    }

    void load()
    const timer = window.setInterval(() => void load(), apiConfig.sensorPollMs)
    return () => {
      controller.abort()
      window.clearInterval(timer)
    }
  }, [key, statusKey, limit, offset, version])

  const current = snapshot && snapshot.key === key ? snapshot : null
  const proposals = useMemo(() => current?.proposals ?? [], [current])

  useEffect(() => {
    const deadlines = proposals
      .map((proposal) => {
        if (proposal.status === 'running' && proposal.endsAt) return Date.parse(proposal.endsAt)
        if (proposal.status === 'pending') return Date.parse(proposal.expiresAt)
        return Number.NaN
      })
      .filter((time) => time > Date.now())
    if (deadlines.length === 0) return
    // The server switches the outlet off at endsAt; give it a few seconds before re-reading.
    const delay = Math.min(Math.min(...deadlines) - Date.now() + 3000, 2 ** 31 - 1)
    const timer = window.setTimeout(refresh, delay)
    return () => window.clearTimeout(timer)
  }, [proposals, refresh])

  const status: Status = current === null ? 'loading' : current.error ? 'error' : 'ready'

  return { proposals, status, error: current?.error ?? '', refresh }
}
