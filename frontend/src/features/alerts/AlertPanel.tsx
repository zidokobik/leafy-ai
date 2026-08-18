import { Icon, type IconName } from '../../components/Icon'
import type { AlertDecision } from '../../types/dashboard'

type AlertPanelProps = {
  decision: AlertDecision
  canControl: boolean
  onDecision: (decision: AlertDecision) => void
}

type AlertContent = {
  eyebrow: string
  title: string
  description: React.ReactNode
  actionLabel: string
  proposedAction: string
  safetyNote: string
  resultIcon?: IconName
  resultText?: string
  reviewLabel?: string
}

const alertContent: Record<AlertDecision, AlertContent> = {
  pending: {
    eyebrow: 'Active alert · Operator authorization required',
    title: 'Nutrient EC is above the safe range',
    description: <>Live EC is <strong>2.7 mS/cm</strong> against a scheduled target of 2.1. Prolonged exposure risks root burn and dehydration.</>,
    actionLabel: 'Proposed schedule change',
    proposedAction: 'Pause dosing · controlled dilution',
    safetyNote: 'No device command will run without approval from an authorized operator.',
  },
  authorized: {
    eyebrow: 'Authorized by Alex Morgan · Command queued',
    title: 'EC corrective action has been authorized',
    description: 'Authorized at 10:43 AM. The command is queued for a final device safety check before execution.',
    actionLabel: 'Authorized response',
    proposedAction: 'Pause dosing · controlled dilution',
    safetyNote: 'Approved by Alex Morgan. Execution remains subject to the final safety check.',
    resultIcon: 'check',
    resultText: 'Authorized · Alex Morgan',
    reviewLabel: 'Revoke authorization',
  },
  rejected: {
    eyebrow: 'Response rejected · Alert remains active',
    title: 'Nutrient EC is above the safe range',
    description: 'No device command was sent. Live EC remains at 2.7 mS/cm and requires another operator decision.',
    actionLabel: 'Proposed schedule change',
    proposedAction: 'No corrective action scheduled',
    safetyNote: 'The greenhouse remains in its current state until a new action is authorized.',
    resultIcon: 'x',
    resultText: 'Rejected · no command sent',
    reviewLabel: 'Review again',
  },
}

export function AlertPanel({ canControl, decision, onDecision }: AlertPanelProps) {
  const content = alertContent[decision]

  return (
    <section className={`alerts-panel ${decision}`} id="alerts" aria-labelledby="alerts-title">
      <div className="alerts-heading">
        <span className="alert-symbol"><Icon name="alert" size={20} /></span>
        <div>
          <span className="alert-eyebrow">{content.eyebrow}</span>
          <h2 id="alerts-title">{content.title}</h2>
          <p>{content.description}</p>
        </div>
      </div>

      <div className="alert-risk">
        <span>{content.actionLabel}</span>
        <strong>{content.proposedAction}</strong>
        <small>{content.safetyNote}</small>
      </div>

      <div className="alert-actions">
        {decision === 'pending' ? (
          <>
            <button
              className="authorize-action"
              type="button"
              disabled={!canControl}
              onClick={() => onDecision('authorized')}
              title={canControl ? undefined : 'Advanced operator access required'}
            >
              {canControl ? 'Authorize response' : 'Advanced access required'}
              <Icon name={canControl ? 'check' : 'lock'} size={14} />
            </button>
            <button type="button" disabled={!canControl} onClick={() => onDecision('rejected')}>Reject</button>
          </>
        ) : (
          <>
            <div className={`authorization-result ${decision}`}>
              <Icon name={content.resultIcon!} size={14} />
              {content.resultText}
            </div>
            <button type="button" disabled={!canControl} onClick={() => onDecision('pending')}>{content.reviewLabel}</button>
          </>
        )}
      </div>
    </section>
  )
}
