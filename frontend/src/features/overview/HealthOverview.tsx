import { Icon } from '../../components/Icon'
import { useLatestMonitoring } from '../monitoring/useMonitoringData'

export function HealthOverview() {
  const monitoring = useLatestMonitoring()
  const healthLabel = monitoring.latest.status === 'attention' ? 'Action needed' : 'All systems healthy'

  return (
    <section className="overview-strip" aria-label="Current greenhouse conditions">
      <div className={`health-summary ${monitoring.latest.status}`}>
        <span className="health-icon"><Icon name="leaf" size={23} /></span>
        <div><span>Greenhouse health</span><strong>{healthLabel}</strong></div>
        <span className="health-score">{monitoring.latest.healthScore} / 100</span>
      </div>
      <div className="metric-grid">
        {monitoring.metrics.map((metric) => (
          <article className={metric.alert ? 'metric-card alert' : 'metric-card'} key={metric.label}>
            <span className={`metric-icon ${metric.tone}`}><Icon name={metric.icon} size={18} /></span>
            <div>
              <span>{metric.label}</span>
              <strong>{metric.value}</strong>
              <small><i />{metric.note}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  )
}
