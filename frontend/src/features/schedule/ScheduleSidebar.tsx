import { Icon } from '../../components/Icon'

type ScheduleSidebarProps = {
  recommendationApplied: boolean
  canControl: boolean
  onToggleRecommendation: () => void
}

export function ScheduleSidebar({ canControl, recommendationApplied, onToggleRecommendation }: ScheduleSidebarProps) {
  return (
    <aside className="side-stack">
      <section className="panel cycle-panel">
        <div className="panel-header">
          <div>
            <span className="section-kicker">Current grow cycle</span>
            <h2>Sweet basil</h2>
          </div>
          <span className="on-track"><Icon name="check" size={13} />On track</span>
        </div>
        <div className="cycle-visual">
          <div className="cycle-ring"><span><strong>31</strong><small>day</small></span></div>
          <div>
            <span>Day 31 of 45</span>
            <strong>14 days to harvest</strong>
            <small>Estimated 13 August</small>
          </div>
        </div>
        <div className="progress-track"><span style={{ width: '68%' }} /></div>
        <div className="cycle-footer"><span>Vegetative</span><strong>68% complete</strong></div>
      </section>

      <section className={recommendationApplied ? 'recommendation-card applied' : 'recommendation-card'}>
        <span className="recommendation-icon">
          <Icon name={recommendationApplied ? 'check' : 'sun'} size={20} />
        </span>
        <div>
          <span>{recommendationApplied ? 'Authorized for today’s schedule' : 'Recommendation · Authorization required'}</span>
          <h3>{recommendationApplied ? 'Today’s light cycle will end 30 min earlier' : 'Shorten today’s light cycle by 30 min'}</h3>
          <p>
            {recommendationApplied
              ? 'The KP303 outlet will switch the light off after 690 min. The normal 720 min cycle returns tomorrow.'
              : 'Based on rising leaf temperature. This uses the KP303 timer without implying unsupported dimming control.'}
          </p>
          <button
            type="button"
            disabled={!canControl}
            onClick={onToggleRecommendation}
            title={canControl ? undefined : 'Advanced operator access required'}
          >
            {canControl
              ? recommendationApplied ? 'Revoke authorization' : 'Authorize schedule change'
              : 'Advanced access required'}
            <Icon name={canControl ? recommendationApplied ? 'x' : 'arrow' : 'lock'} size={14} />
          </button>
        </div>
      </section>

      <section className="panel next-event">
        <span className="clock-icon"><Icon name="clock" size={20} /></span>
        <div>
          <span>Next scheduled change</span>
          <strong>{recommendationApplied ? 'Light off 30 min early' : 'Light off'}</strong>
          <small>{recommendationApplied ? 'Today at 5:30 PM · safety adjustment' : 'Today at 6:00 PM · in 7h 18m'}</small>
        </div>
        <Icon name="chevron" size={16} />
      </section>
    </aside>
  )
}
