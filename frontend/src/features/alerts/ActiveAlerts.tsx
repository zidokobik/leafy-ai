import { XIcon } from 'lucide-react'
import { Alert, AlertAction, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import type { FarmAlert } from '../../api/alerts'
import { alertTime, severityMeta } from './severity'
import { useActiveAlerts } from './useActiveAlerts'

function AlertItem({ alert, onDismiss }: { alert: FarmAlert, onDismiss: (alertId: string) => void }) {
  const { label, Icon } = severityMeta[alert.severity]
  return (
    <Alert variant={alert.severity === 'critical' ? 'destructive' : 'default'}>
      <Icon />
      <AlertTitle>{alert.title}</AlertTitle>
      <AlertDescription>
        {alert.message}
        <span className="block text-xs">
          {label} · last raised {alertTime.format(Date.parse(alert.updatedAt))}
          {alert.occurrences > 1 ? ` · seen ${alert.occurrences} times` : ''}
        </span>
      </AlertDescription>
      <AlertAction>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="Dismiss alert"
          title="Hide from Overview. The alert stays active until resolved on the Alerts page."
          onClick={() => onDismiss(alert.alertId)}
        >
          <XIcon />
        </Button>
      </AlertAction>
    </Alert>
  )
}

/** Active, not dismissed alerts pinned before everything else on the Overview page. */
export function ActiveAlerts() {
  const { alerts, status, dismiss } = useActiveAlerts()

  if (status === 'error' && alerts.length === 0) {
    return <p className="text-sm text-muted-foreground">Unable to load alerts.</p>
  }
  if (alerts.length === 0) return null

  return (
    <section className="flex flex-col gap-2" aria-label="Active alerts">
      {alerts.map((alert) => (
        <AlertItem key={alert.alertId} alert={alert} onDismiss={(alertId) => void dismiss(alertId)} />
      ))}
    </section>
  )
}
