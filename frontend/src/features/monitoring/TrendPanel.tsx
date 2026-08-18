import { Icon } from '../../components/Icon'
import { monitorLabels } from '../../data/dashboard'
import type { MonitorRange, TrendSeries } from '../../types/dashboard'

type TrendPanelProps = {
  range: MonitorRange
  series: TrendSeries[]
  snapshot: string
}

export function TrendPanel({ range, series, snapshot }: TrendPanelProps) {
  return (
    <article className="panel trend-panel">
      <div className="trend-panel-head">
        <div>
          <span className="section-kicker">Synchronized trends</span>
          <h3>Environment + controls</h3>
        </div>
        <div className="selected-snapshot">
          <span>Selected point</span>
          <strong>{snapshot}</strong>
        </div>
      </div>

      <div className="trend-key">
        <span><i className="target-key" />Target range</span>
        <span><i className="alert-key" />Outside safe range</span>
        <small>All rows share the same time axis</small>
      </div>

      <div className="trend-rows">
        {series.map((trend) => (
          <div className={trend.alert ? 'trend-row alert' : 'trend-row'} key={trend.label}>
            <div className="trend-label">
              <i className={trend.tone} />
              <span>{trend.label}<small>Target {trend.target}</small></span>
              <strong>{trend.value}</strong>
            </div>
            <div className={`spark-chart ${trend.tone}`}>
              <svg
                viewBox="0 0 600 42"
                preserveAspectRatio="none"
                role="img"
                aria-label={`${trend.label} trend, current value ${trend.value}`}
              >
                <rect className="target-band" x="0" y="13" width="600" height="16" rx="5" />
                <path d={trend.path} />
                <line className="selected-line" x1="456" y1="0" x2="456" y2="42" />
                <circle cx="456" cy={trend.pointY} r="4" />
              </svg>
            </div>
          </div>
        ))}
      </div>

      <div className="shared-time-axis">
        {monitorLabels[range].map((label) => <span key={label}>{label}</span>)}
      </div>

      <div className="trend-alert-note">
        <span><Icon name="alert" size={16} /></span>
        <div>
          <strong>EC moved outside its safe range at 10:24 AM</strong>
          <small>Temperature, humidity, fan, light and pH remained within target at the same time.</small>
        </div>
        <a href="#alerts">View alert <Icon name="arrow" size={13} /></a>
      </div>
    </article>
  )
}
