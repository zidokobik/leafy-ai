import { useRef, useState, type FormEvent } from 'react'
import { MailCheckIcon, MailWarningIcon } from 'lucide-react'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Field, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { ApiError } from '../../api/client'
import type { EmailLog } from '../../api/notifications'
import { notificationsApi } from '../../api/notifications'
import { useEmailNotifications } from './useEmailNotifications'

const logTime = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

function errorMessage(cause: unknown, fallback: string) {
  if (cause instanceof ApiError && cause.details && typeof cause.details === 'object') {
    const detail = (cause.details as { detail?: unknown }).detail
    if (typeof detail === 'string') return detail
  }
  return fallback
}

function AddRecipientForm({ busy, onAdd }: { busy: boolean; onAdd: (email: string, label: string) => Promise<boolean> }) {
  const [email, setEmail] = useState('')
  const [label, setLabel] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (await onAdd(email.trim(), label.trim())) {
      setEmail('')
      setLabel('')
    }
  }

  return (
    <form onSubmit={submit} className="flex flex-col gap-3 sm:flex-row sm:items-end">
      <Field className="flex-1">
        <FieldLabel htmlFor="recipient-email">Email</FieldLabel>
        <Input
          id="recipient-email"
          type="email"
          required
          maxLength={254}
          placeholder="admin@example.com"
          value={email}
          disabled={busy}
          onChange={(event) => setEmail(event.target.value)}
        />
      </Field>
      <Field className="flex-1">
        <FieldLabel htmlFor="recipient-label">Label (optional)</FieldLabel>
        <Input
          id="recipient-label"
          maxLength={120}
          placeholder="Farm manager"
          value={label}
          disabled={busy}
          onChange={(event) => setLabel(event.target.value)}
        />
      </Field>
      <Button type="submit" disabled={busy} className="sm:w-auto">
        Add recipient
      </Button>
    </form>
  )
}

function EmailLogRow({ log }: { log: EmailLog }) {
  const failed = log.status === 'failed'
  const Icon = failed ? MailWarningIcon : MailCheckIcon
  return (
    <div className="flex items-start gap-3 rounded-lg border p-3">
      <Icon className={`mt-0.5 size-4 shrink-0 ${failed ? 'text-destructive' : 'text-muted-foreground'}`} />
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <p className="font-medium">{log.subject}</p>
          <Badge variant={failed ? 'destructive' : 'secondary'}>{failed ? 'Failed' : 'Sent'}</Badge>
          <Badge variant="outline">{log.triggeredBy === 'agent' ? 'Agent' : 'Test'}</Badge>
        </div>
        <p className="mt-1 break-all text-sm text-muted-foreground">To {log.recipients.join(', ')}</p>
        {log.error && <p className="mt-1 text-sm text-destructive">{log.error}</p>}
        <p className="mt-1 text-xs text-muted-foreground">{logTime.format(Date.parse(log.createdAt))}</p>
      </div>
    </div>
  )
}

/** Admin email recipients and the send log, shown on the Alerts page. */
export function EmailNotifications() {
  const { recipients, logs, status, error, refresh } = useEmailNotifications()
  const [busy, setBusy] = useState(false)
  const [actionError, setActionError] = useState('')
  const [testResult, setTestResult] = useState('')
  const lock = useRef(false)

  async function act(run: () => Promise<unknown>, fallback: string): Promise<boolean> {
    if (lock.current) return false
    lock.current = true
    setBusy(true)
    setActionError('')
    let ok = false
    try {
      await run()
      ok = true
    } catch (cause) {
      setActionError(errorMessage(cause, fallback))
    } finally {
      lock.current = false
      setBusy(false)
      refresh()
    }
    return ok
  }

  async function sendTest() {
    if (lock.current) return
    lock.current = true
    setBusy(true)
    setActionError('')
    setTestResult('')
    try {
      const log = await notificationsApi.sendTestEmail()
      if (log.status === 'sent') setTestResult(`Test email sent to ${log.recipients.join(', ')}.`)
      else setActionError(`Send failed: ${log.error ?? 'unknown SMTP error'}`)
    } catch (cause) {
      setActionError(errorMessage(cause, 'Unable to send the test email.'))
    } finally {
      lock.current = false
      setBusy(false)
      refresh()
    }
  }

  return (
    <>
      {(error || actionError) && (
        <Alert variant="destructive">
          <AlertDescription>{actionError || error}</AlertDescription>
        </Alert>
      )}
      <Card>
        <CardHeader>
          <CardTitle>Email recipients</CardTitle>
          <CardDescription>
            Admins the agent emails for critical conditions and requested reports. Disabled recipients
            are kept but skipped. SMTP credentials are configured in the server&apos;s .env file.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <AddRecipientForm
            busy={busy}
            onAdd={(email, label) =>
              act(() => notificationsApi.addRecipient(email, label || null), 'Unable to add the recipient.')
            }
          />
          {status === 'loading' && <p role="status">Loading recipients…</p>}
          {status !== 'loading' && recipients.length === 0 && (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No recipients yet</EmptyTitle>
                <EmptyDescription>Add at least one admin email to receive notifications.</EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {recipients.map((recipient) => (
            <div
              key={recipient.recipientId}
              className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center"
            >
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="break-all font-medium">{recipient.email}</p>
                  {!recipient.enabled && <Badge variant="outline">Disabled</Badge>}
                </div>
                {recipient.label && <p className="mt-1 text-sm text-muted-foreground">{recipient.label}</p>}
              </div>
              <div className="flex shrink-0 gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    void act(
                      () => notificationsApi.setRecipientEnabled(recipient.recipientId, !recipient.enabled),
                      'Unable to update the recipient.',
                    )
                  }
                >
                  {recipient.enabled ? 'Disable' : 'Enable'}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy}
                  onClick={() =>
                    void act(
                      () => notificationsApi.deleteRecipient(recipient.recipientId),
                      'Unable to remove the recipient.',
                    )
                  }
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle>Email log</CardTitle>
          <CardDescription>Every send attempt, including failures, most recent first.</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
            <Button variant="outline" size="sm" disabled={busy} onClick={() => void sendTest()}>
              {busy ? 'Working…' : 'Send test email'}
            </Button>
            {testResult && <p className="text-sm text-muted-foreground">{testResult}</p>}
          </div>
          {status === 'loading' && <p role="status">Loading email log…</p>}
          {status !== 'loading' && logs.length === 0 && (
            <Empty>
              <EmptyHeader>
                <EmptyTitle>No emails sent yet</EmptyTitle>
                <EmptyDescription>
                  The agent emails the recipients above when a critical condition needs a human or a
                  report is requested.
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {logs.map((log) => (
            <EmailLogRow key={log.emailId} log={log} />
          ))}
        </CardContent>
      </Card>
    </>
  )
}
