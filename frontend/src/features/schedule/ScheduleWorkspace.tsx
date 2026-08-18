import type { AlertDecision } from '../../types/dashboard'
import { SchedulePanel } from './SchedulePanel'
import { ScheduleSidebar } from './ScheduleSidebar'
import { useScheduleControls } from './useScheduleControls'

type ScheduleWorkspaceProps = {
  decision: AlertDecision
  canControl: boolean
}

export function ScheduleWorkspace({ canControl, decision }: ScheduleWorkspaceProps) {
  const schedule = useScheduleControls()

  return (
    <div className="main-grid">
      <SchedulePanel
        decision={decision}
        manualMode={schedule.manualMode}
        controls={schedule.controls}
        saved={schedule.saved}
        canControl={canControl}
        onChangeControlDuration={schedule.changeControlDuration}
        onToggleControl={schedule.toggleControl}
        onEnableManualMode={schedule.enableManualMode}
        onResetSchedule={schedule.resetSchedule}
        onSaveManualSettings={schedule.saveManualSettings}
      />
      <ScheduleSidebar
        canControl={canControl}
        recommendationApplied={schedule.recommendationApplied}
        onToggleRecommendation={schedule.toggleRecommendation}
      />
    </div>
  )
}
