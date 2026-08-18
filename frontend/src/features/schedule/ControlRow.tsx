import { Icon } from '../../components/Icon'
import type { ControlKey, ControlSetting, ControlValue } from '../../types/dashboard'

type ControlRowProps = {
  controlKey: ControlKey
  setting: ControlSetting
  value: ControlValue
  manualMode: boolean
  canControl: boolean
  onChangeDuration: (key: ControlKey, value: number) => void
  onToggle: (key: ControlKey) => void
}

function formatValue(value: number, setting: ControlSetting) {
  return `${value} ${setting.durationUnit}`
}

function formatCountdown(totalSeconds: number) {
  const safeSeconds = Math.max(0, totalSeconds)
  const hours = Math.floor(safeSeconds / 3600)
  const minutes = Math.floor((safeSeconds % 3600) / 60)
  const seconds = safeSeconds % 60

  if (hours > 0) {
    return `${hours}h ${minutes}m`
  }

  if (minutes > 0) {
    return `${minutes}m ${seconds}s`
  }

  return `${seconds}s`
}

export function ControlRow({
  controlKey,
  setting,
  value,
  manualMode,
  canControl,
  onChangeDuration,
  onToggle,
}: ControlRowProps) {
  const changeBy = (delta: number) => onChangeDuration(controlKey, value.duration + delta)
  const controlsEnabled = manualMode && canControl

  return (
    <div className="control-row">
      <span className={`control-icon ${setting.tone}`}><Icon name={setting.icon} size={20} /></span>
      <div className="control-name">
        <div className="control-title">
          <strong>{setting.label}</strong>
          <span className={`risk-badge ${setting.risk}`}>{setting.risk} risk</span>
        </div>
        <small>{setting.description}</small>
        <div
          className={`device-runtime ${value.enabled ? 'running' : 'waiting'} ${setting.alert ? 'alert' : ''}`}
          aria-label={`${setting.label} live timing status`}
        >
          <span className="runtime-state"><i />{value.enabled ? 'Running' : 'Off'}</span>
          {value.enabled ? (
            <div className="runtime-timing">
              <span>Run <strong>{formatCountdown(value.elapsedSeconds)}</strong></span>
              <span>Remaining <strong>{formatCountdown(value.remainingSeconds)}</strong></span>
            </div>
          ) : (
            <div className="runtime-timing next-start">
              <span>Next start <strong>{formatCountdown(value.nextStartSeconds)}</strong></span>
            </div>
          )}
        </div>
      </div>

      <div className="power-control">
        <span>Power</span>
        <label className="power-switch">
          <input
            type="checkbox"
            role="switch"
            checked={value.enabled}
            disabled={!controlsEnabled}
            onChange={() => onToggle(controlKey)}
            aria-label={`${setting.label} power`}
          />
          <i aria-hidden="true" />
          <b>{value.enabled ? 'On' : 'Off'}</b>
        </label>
      </div>

      <div className="slider-wrap duration-control">
        <span>Run time</span>
        <input
          type="range"
          min={setting.min}
          max={setting.max}
          step={setting.step}
          value={value.duration}
          disabled={!controlsEnabled}
          onChange={(event) => onChangeDuration(controlKey, Number(event.target.value))}
          aria-label={`${setting.label} run time in ${setting.durationUnit}`}
        />
        <div className="slider-limits">
          <span>{formatValue(setting.min, setting)}</span>
          <span>{formatValue(setting.max, setting)}</span>
        </div>
      </div>

      <div className="stepper">
        <button
          type="button"
          disabled={!controlsEnabled}
          onClick={() => changeBy(-setting.step)}
          aria-label={`Decrease ${setting.label}`}
        >
          <Icon name="minus" size={15} />
        </button>
        <output aria-live="polite">{formatValue(value.duration, setting)}</output>
        <button
          type="button"
          disabled={!controlsEnabled}
          onClick={() => changeBy(setting.step)}
          aria-label={`Increase ${setting.label}`}
        >
          <Icon name="plus" size={15} />
        </button>
      </div>
    </div>
  )
}
