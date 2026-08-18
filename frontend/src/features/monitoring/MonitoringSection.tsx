import { useState } from 'react'
import { Icon } from '../../components/Icon'
import { monitorRanges } from '../../data/dashboard'
import type { MonitorRange } from '../../types/dashboard'
import { CameraPanel } from './CameraPanel'
import { TrendPanel } from './TrendPanel'
import { useMonitoringHistory } from './useMonitoringData'

export function MonitoringSection() {
  const [range, setRange] = useState<MonitorRange>('24H')
  const monitoring = useMonitoringHistory(range)

  return (
    <section className="monitoring-section" id="monitoring">
      <div className="monitoring-heading">
        <div>
          <span className="section-kicker"><Icon name="activity" size={14} />Long-term monitoring</span>
          <h2>See every variable on the same timeline</h2>
          <p>Compare the live environment with device output and nutrient conditions.</p>
        </div>
        <div className="monitor-range-tabs" aria-label="Monitoring time range">
          {monitorRanges.map((monitorRange) => (
            <button
              className={range === monitorRange ? 'active' : ''}
              type="button"
              onClick={() => setRange(monitorRange)}
              key={monitorRange}
            >
              {monitorRange}
            </button>
          ))}
        </div>
      </div>

      <div className="monitoring-grid">
        <CameraPanel />
        <TrendPanel range={range} series={monitoring.series} snapshot={monitoring.snapshot} />
      </div>
    </section>
  )
}
