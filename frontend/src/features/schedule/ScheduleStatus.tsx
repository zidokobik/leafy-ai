import { Icon } from '../../components/Icon'
import type { AlertDecision } from '../../types/dashboard'

type ScheduleStatusProps = {
  decision: AlertDecision
}

const statusContent = {
  pending: {
    timeline: 'Now · approval required',
    eyebrow: 'Alert blocks automatic device control',
    title: 'EC correction is waiting for approval',
    description: 'The schedule recommends pausing nutrient dosing and starting controlled dilution, but cannot execute it without operator authorization.',
    authorization: 'Awaiting operator',
    device: 'Blocked',
  },
  authorized: {
    timeline: 'Now · response authorized',
    eyebrow: 'Operator authorization received',
    title: 'EC correction is queued for execution',
    description: 'The approved dosing pause and controlled dilution will run after the final device safety check.',
    authorization: 'Alex · 10:43 AM',
    device: 'Queued',
  },
  rejected: {
    timeline: 'Now · response rejected',
    eyebrow: 'Alert blocks automatic device control',
    title: 'EC response was rejected',
    description: 'No automatic operation was executed. The alert remains active for operator review.',
    authorization: 'Rejected',
    device: 'Not sent',
  },
} satisfies Record<AlertDecision, {
  timeline: string
  eyebrow: string
  title: string
  description: string
  authorization: string
  device: string
}>

export function ScheduleStatus({ decision }: ScheduleStatusProps) {
  const content = statusContent[decision]

  return (
    <>
      <div className="schedule-timeline" aria-label="Today's growing schedule">
        <div className="timeline-track">
          <span className="night-block start" />
          <span className="day-block" />
          <span className="night-block end" />
          <i className="now-marker responding" style={{ left: '44%' }}><b>{content.timeline}</b></i>
        </div>
        <div className="timeline-labels"><span>6 AM</span><span>12 PM</span><span>6 PM</span><span>12 AM</span></div>
      </div>

      <div className="schedule-response" role="status">
        <span className="response-icon"><Icon name="alert" size={18} /></span>
        <div className="response-copy">
          <span>{content.eyebrow}</span>
          <strong>{content.title}</strong>
          <p>{content.description}</p>
        </div>
        <div className="response-steps">
          <span><i className="done" /><small>Detected</small><b>10:24 AM</b></span>
          <span>
            <i className={decision === 'authorized' ? 'done' : decision === 'pending' ? 'active' : ''} />
            <small>Authorization</small>
            <b>{content.authorization}</b>
          </span>
          <span>
            <i className={decision === 'authorized' ? 'active' : ''} />
            <small>Device command</small>
            <b>{content.device}</b>
          </span>
        </div>
      </div>
    </>
  )
}
