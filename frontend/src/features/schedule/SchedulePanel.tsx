import { Icon } from '../../components/Icon'
import { controlKeys, controlSettings } from '../../data/dashboard'
import type { AlertDecision, ControlKey, ControlValues } from '../../types/dashboard'
import { ControlRow } from './ControlRow'
import { ScheduleStatus } from './ScheduleStatus'

type SchedulePanelProps = {
  decision: AlertDecision
  manualMode: boolean
  controls: ControlValues
  saved: boolean
  canControl: boolean
  onChangeControlDuration: (key: ControlKey, value: number) => void
  onToggleControl: (key: ControlKey) => void
  onEnableManualMode: () => void
  onResetSchedule: () => void
  onSaveManualSettings: () => void
}

export function SchedulePanel({
  decision,
  manualMode,
  controls,
  saved,
  canControl,
  onChangeControlDuration,
  onToggleControl,
  onEnableManualMode,
  onResetSchedule,
  onSaveManualSettings,
}: SchedulePanelProps) {
  return (
    <section className="panel schedule-panel" id="schedule">
      <div className="panel-header schedule-header">
        <div>
          <span className="section-kicker"><Icon name="schedule" size={14} />Safe adaptive schedule</span>
          <h2>Sweet basil · Vegetative Week 5</h2>
          <p>Growth-optimised targets with unattended safety guardrails</p>
        </div>
        <div className={`mode-pill ${!canControl ? 'readonly' : manualMode ? 'manual' : ''}`}>
          {!canControl ? <Icon name="lock" size={13} /> : <i />}
          {!canControl
            ? 'Viewer · controls locked'
            : manualMode ? 'Manual override active' : 'Safety guardrails active'}
        </div>
      </div>

      <div className="schedule-policy" aria-label="Schedule operating policy">
        <div><span>Growth goal</span><strong>Steady leaf growth</strong></div>
        <div><span>Unattended window</span><strong>Now–6:00 PM</strong></div>
        <div><span>Control priority</span><strong>Safety → stability → yield</strong></div>
      </div>

      <ScheduleStatus decision={decision} />

      <div className="control-intro">
        <div>
          <h3>{manualMode ? 'Manual override settings' : 'Schedule targets & live response'}</h3>
          <p>
            {manualMode
              ? 'Power states and timers remain active until you return control to the safe schedule.'
              : 'KP303 outlets use timed on/off control. Manual control overrides automatic responses.'}
          </p>
        </div>
        {!manualMode && (
          <button
            className="outline-button"
            type="button"
            disabled={!canControl}
            onClick={onEnableManualMode}
            title={canControl ? undefined : 'Advanced operator access required'}
          >
            {!canControl && <Icon name="lock" size={14} />}
            {canControl ? 'Take manual control' : 'View only'}
          </button>
        )}
      </div>

      <div className="control-list" id="devices">
        {controlKeys.map((key) => (
          <ControlRow
            controlKey={key}
            setting={controlSettings[key]}
            value={controls[key]}
            manualMode={manualMode}
            canControl={canControl}
            onChangeDuration={onChangeControlDuration}
            onToggle={onToggleControl}
            key={key}
          />
        ))}
      </div>

      {manualMode && (
        <div className="manual-actions">
          <div className={saved ? 'save-note visible' : 'save-note'}>
            <Icon name="check" size={15} />
            Manual settings applied
          </div>
          <button className="text-button" type="button" onClick={onResetSchedule}>Return to schedule</button>
          <button className="primary-button" type="button" onClick={onSaveManualSettings}>Apply settings</button>
        </div>
      )}
    </section>
  )
}
