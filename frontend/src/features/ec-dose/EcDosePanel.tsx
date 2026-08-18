import { useEffect, useState } from 'react'
import type { EcDoseSettings } from '../../api/contracts'
import { Icon } from '../../components/Icon'
import { useEcDoseController } from './useEcDoseController'

type EcDosePanelProps = {
  canControl: boolean
}

type SettingKey = keyof EcDoseSettings

type SettingDefinition = {
  key: SettingKey
  label: string
  description: string
  unit: string
  min: number
  max: number
  step: number
}

const settings: SettingDefinition[] = [
  {
    key: 'targetEc',
    label: 'Target EC',
    description: 'Nutrient strength setpoint',
    unit: 'µS/cm',
    min: 500,
    max: 5000,
    step: 50,
  },
  {
    key: 'movingAverage',
    label: 'Moving average',
    description: 'Sensor smoothing window',
    unit: 'min',
    min: 1,
    max: 30,
    step: 1,
  },
  {
    key: 'doseOnTime',
    label: 'Dose on time',
    description: 'Pump run time per cycle',
    unit: 'sec',
    min: 1,
    max: 120,
    step: 1,
  },
  {
    key: 'mixingGuard',
    label: 'Mixing guard',
    description: 'Wait time before rechecking EC',
    unit: 'min',
    min: 1,
    max: 30,
    step: 1,
  },
  {
    key: 'maxCycles',
    label: 'Max cycles / hour',
    description: 'Hourly dosing safety limit',
    unit: 'cycles',
    min: 1,
    max: 30,
    step: 1,
  },
]

function formatClock(date: Date) {
  return new Intl.DateTimeFormat('en-AU', {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
  }).format(date)
}

function formatCountdown(totalSeconds: number) {
  const safeSeconds = Math.max(0, Math.round(totalSeconds))
  const minutes = Math.floor(safeSeconds / 60)
  const seconds = safeSeconds % 60
  return minutes > 0 ? `${minutes} min ${seconds} sec` : `${seconds} sec`
}

function formatTimer(totalSeconds: number) {
  const safeSeconds = Math.max(0, Math.round(totalSeconds))
  const minutes = Math.floor(safeSeconds / 60).toString().padStart(2, '0')
  const seconds = (safeSeconds % 60).toString().padStart(2, '0')
  return `${minutes}:${seconds}`
}

function formatEventType(type: string) {
  if (type === 'dose_completed') return 'Dose completed'
  if (type === 'dose_blocked') return 'Dose blocked'
  if (type === 'settings_updated') return 'Settings updated'
  return 'No dosing events'
}

export function EcDosePanel({ canControl }: EcDosePanelProps) {
  const controller = useEcDoseController()
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const changeValue = (setting: SettingDefinition, direction: -1 | 1) => {
    controller.saveSettings({
      ...controller.settings,
      [setting.key]: Math.min(
        setting.max,
        Math.max(setting.min, controller.settings[setting.key] + setting.step * direction),
      ),
    })
  }

  const nextStart = controller.live.nextStartAt ? new Date(controller.live.nextStartAt) : null
  const nextStartSeconds = nextStart ? (nextStart.getTime() - now.getTime()) / 1000 : 0
  const targetDifference = controller.settings.targetEc - controller.live.movingAverageEc
  const targetProgress = Math.min(100, controller.live.movingAverageEc / controller.settings.targetEc * 100)
  const validPercent = controller.live.totalSamples === 0
    ? 0
    : Math.round(controller.live.validSamples / controller.live.totalSamples * 100)
  const lastEventAt = controller.live.lastEvent.occurredAt
    ? formatClock(new Date(controller.live.lastEvent.occurredAt))
    : 'Not available'
  const connectionLabel = controller.connectionState === 'error'
    ? 'Backend unavailable · showing last data'
    : controller.connectionState === 'loading'
      ? 'Connecting to controller'
      : controller.connectionState === 'connected'
        ? 'Controller connected'
        : 'Automatic dosing active'

  return (
    <section className="panel ec-dose-panel" id="ec-dose">
      <div className="ec-dose-header">
        <div>
          <span className="section-kicker"><Icon name="trend" size={14} />Nutrient control</span>
          <h2>EC dose control</h2>
          <p>Closed-loop dosing settings and live controller feedback</p>
        </div>
        <div className={`ec-controller-status ${canControl ? '' : 'readonly'}`}>
          {canControl ? <i /> : <Icon name="lock" size={13} />}
          {canControl ? connectionLabel : 'Viewer · controls locked'}
        </div>
      </div>

      <div className="ec-dose-layout">
        <div className="ec-settings" aria-label="EC dosing settings">
          <div className="ec-section-heading">
            <div>
              <span>Control parameters</span>
              <strong>Dosing configuration</strong>
            </div>
            <button
              type="button"
              disabled={!canControl}
              onClick={controller.resetSettings}
            >
              Reset defaults
            </button>
          </div>

          <div className="ec-setting-list">
            {settings.map((setting) => (
              <div className="ec-setting-row" key={setting.key}>
                <div>
                  <strong>{setting.label}</strong>
                  <small>{setting.description}</small>
                </div>
                <div className="ec-stepper">
                  <button
                    type="button"
                    disabled={!canControl || controller.settings[setting.key] <= setting.min}
                    onClick={() => changeValue(setting, -1)}
                    aria-label={`Decrease ${setting.label}`}
                  >
                    <Icon name="minus" size={16} />
                  </button>
                  <output aria-live="polite">
                    <strong>{controller.settings[setting.key].toLocaleString()}</strong>
                    <span>{setting.unit}</span>
                  </output>
                  <button
                    type="button"
                    disabled={!canControl || controller.settings[setting.key] >= setting.max}
                    onClick={() => changeValue(setting, 1)}
                    aria-label={`Increase ${setting.label}`}
                  >
                    <Icon name="plus" size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        <aside className="ec-live-panel" aria-label="Live EC dose data">
          <div className="ec-live-heading">
            <div>
              <span className="live-indicator"><i />Live data</span>
              <h3>Controller status</h3>
            </div>
            <small title={controller.apiError ?? undefined}>
              Updated {formatClock(new Date(controller.live.updatedAt))}
            </small>
          </div>

          <div className="ec-primary-reading">
            <span>EC moving average</span>
            <strong>{controller.live.movingAverageEc.toLocaleString()} <small>µS/cm</small></strong>
            <div className="ec-target-progress">
              <span style={{ width: `${targetProgress}%` }} />
            </div>
            <p>
              <Icon name="trend" size={13} />
              {Math.abs(targetDifference).toLocaleString()} µS/cm {targetDifference >= 0 ? 'below' : 'above'} target
            </p>
          </div>

          <dl className="ec-live-grid">
            <div>
              <dt>Valid history</dt>
              <dd>{controller.live.validSamples} / {controller.live.totalSamples} <small>samples</small></dd>
              <span className="data-quality"><i />{validPercent}% valid</span>
            </div>
            <div>
              <dt>Next start</dt>
              <dd>{nextStart ? formatClock(nextStart) : 'Not scheduled'}</dd>
              <span>{nextStart ? `in ${formatCountdown(nextStartSeconds)}` : 'Waiting for controller'}</span>
            </div>
            <div className="ec-last-event">
              <dt>Last event</dt>
              <dd>{formatEventType(controller.live.lastEvent.type)}</dd>
              <span>
                {controller.live.lastEvent.durationSeconds === null
                  ? lastEventAt
                  : `${controller.live.lastEvent.durationSeconds} sec pulse · ${lastEventAt}`}
              </span>
            </div>
          </dl>

          <div className="ec-guard-status">
            <span className="guard-icon"><Icon name="clock" size={17} /></span>
            <div>
              <strong>Mixing guard active</strong>
              <small>Next reading must remain valid before dosing</small>
            </div>
            <b>{formatTimer(controller.live.mixingGuardRemainingSeconds)}</b>
          </div>
        </aside>
      </div>
    </section>
  )
}
