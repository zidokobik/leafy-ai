import { useRef, useState } from 'react'
import { CheckIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import type { FarmAlert } from '../../api/alerts'
import { alertsApi } from '../../api/alerts'
import { alertTime, severityMeta } from './severity'
import { useAlertsData } from './useAlertsData'

function ActiveAlertRow({ alert, busy, onDismiss, onResolve }: {
  alert: FarmAlert
  busy: boolean
  onDismiss: (alertId: string) => void
  onResolve: (alertId: string) => void
}) {
  const { label, Icon } = severityMeta[alert.severity]
  const critical = alert.severity === 'critical'
  return (
    <div className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-start">
      <Icon className={`mt-0.5 size-4 shrink-0 ${critical ? 'text-destructive' : 'text-muted-foreground'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{alert.title}</p>
          <Badge variant={critical ? 'destructive' : 'secondary'}>{label}</Badge>
          {alert.dismissedAt && <Badge variant="outline">Hidden from Overview</Badge>}
        </div>
        <p className="mt-1 text-sm text-muted-foreground">{alert.message}</p>
        <p className="mt-1 text-xs text-muted-foreground">
          First raised {alertTime.format(Date.parse(alert.createdAt))}
          {' · '}last raised {alertTime.format(Date.parse(alert.updatedAt))}
          {alert.occurrences > 1 ? ` · seen ${alert.occurrences} times` : ''}
        </p>
      </div>
      <div className="flex shrink-0 gap-2">
        {!alert.dismissedAt && (
          <Button
            variant="ghost"
            size="sm"
            disabled={busy}
            title="Hide from Overview without resolving"
            onClick={() => onDismiss(alert.alertId)}
          >
            Hide
          </Button>
        )}
        <Button variant="outline" size="sm" disabled={busy} onClick={() => onResolve(alert.alertId)}>
          Resolve
        </Button>
      </div>
    </div>
  )
}

export function AlertsPage() {
  const { active, resolved, status, error, refresh } = useAlertsData()
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const lock = useRef(false)

  async function act(run: () => Promise<unknown>) {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setActionError('')
    try {
      await run()
    } catch {
      setActionError('Action failed. The list below has been refreshed; try again.')
    } finally {
      lock.current = false
      setBusy(false)
      refresh()
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-4xl flex-col gap-6 pb-8">
      <header>
        <h1 className="text-2xl font-medium">Alerts</h1>
        <p className="mt-1 text-muted-foreground">
          Alerts raised by the agent. Hiding only removes an alert from the Overview pin; it stays
          active until explicitly resolved here or by the agent. Re-raised alerts reappear.
        </p>
      </header>
      {(error || actionError) && (
        <Alert variant="destructive">
          <AlertDescription>{actionError || error}</AlertDescription>
        </Alert>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Active</CardTitle>
          <CardDescription>Ordered by severity, most recently raised first.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {status === 'loading' && <p role="status">Loading alerts…</p>}
          {status !== 'loading' && active.length === 0 && (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No active alerts</EmptyTitle>
                <EmptyDescription>The agent raises alerts here when something needs attention.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {active.map((alert) => (
            <ActiveAlertRow
              key={alert.alertId}
              alert={alert}
              busy={busy}
              onDismiss={(alertId) => void act(() => alertsApi.dismiss(alertId))}
              onResolve={(alertId) => void act(() => alertsApi.resolve(alertId))}
            />
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Recently resolved</CardTitle>
          <CardDescription>Closed alerts stay here for reference. A new occurrence starts a fresh alert.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {status !== 'loading' && resolved.length === 0 && (
            <p className="text-sm text-muted-foreground">Nothing resolved yet.</p>
          )}
          {resolved.map((alert) => (
            <div key={alert.alertId} className="flex items-start gap-3 rounded-lg border p-3">
              <CheckIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="font-medium">{alert.title}</p>
                  <Badge variant="secondary">{severityMeta[alert.severity].label}</Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{alert.message}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Resolved by {alert.resolvedBy === 'agent' ? 'the agent' : 'a user'}
                  {alert.resolvedAt ? ` ${alertTime.format(Date.parse(alert.resolvedAt))}` : ''}
                  {alert.occurrences > 1 ? ` · was seen ${alert.occurrences} times` : ''}
                </p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </section>
  )
}
