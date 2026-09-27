import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { safetyApi } from '@/api/safety'
import type { SafetyRule, SafetyRuleWrite } from '@/api/safety'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '@/components/ui/card'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from '@/components/ui/dialog'
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from '@/components/ui/empty'
import { Field, FieldGroup, FieldLabel, FieldSet } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { safetyError, useSafetyList } from './useSafetyList'

const blank: SafetyRuleWrite = { deviceId: '', actionType: 'run_for_duration', maxDurationSeconds: 60, cooldownSeconds: 120, enabled: false }

export function SafetyPage() {
  const rules = useSafetyList(safetyApi.rules)
  const [busy, setBusy] = useState(false)
  const lock = useRef(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [editing, setEditing] = useState<SafetyRule | 'new' | null>(null)
  const [form, setForm] = useState<SafetyRuleWrite>(blank)
  const [confirmation, setConfirmation] = useState<{ title: string, description: string, run: () => Promise<string> } | null>(null)

  async function perform(run: () => Promise<string>) {
    if (lock.current) return
    lock.current = true
    setBusy(true); setError(''); setMessage('')
    try {
      setMessage(await run())
      setEditing(null); setConfirmation(null)
    } catch (cause) { setError(`${safetyError(cause)} Check the latest records before retrying.`) }
    finally {
      lock.current = false; setBusy(false)
      rules.refresh()
    }
  }
  function edit(rule: SafetyRule | 'new') {
    setError(''); setEditing(rule)
    setForm(rule === 'new' ? { ...blank } : { deviceId: rule.deviceId, actionType: rule.actionType, maxDurationSeconds: rule.maxDurationSeconds, cooldownSeconds: rule.cooldownSeconds, enabled: rule.enabled })
  }
  function submit(event: FormEvent) {
    event.preventDefault()
    void perform(async () => {
      await safetyApi.saveRule(form, editing && editing !== 'new' ? editing.ruleId : undefined)
      return 'Safety rule saved.'
    })
  }
  return <section className="mx-auto flex w-full max-w-6xl flex-col gap-6 pb-8">
    <header><h1 className="text-2xl font-medium">Safety</h1><p className="text-muted-foreground">Manage safety limits. Review operation requests on the Logs page.</p></header>
    {message && <Alert role="status"><AlertDescription>{message}</AlertDescription></Alert>}
    {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
    <Card>
      <CardHeader><CardTitle>Safety rules</CardTitle><CardDescription>One rule per device and action. Missing or disabled rules block new approvals.</CardDescription></CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div className="flex gap-2"><Button disabled={busy} onClick={() => edit('new')}>New rule</Button><Button variant="outline" disabled={busy || rules.status === 'loading'} onClick={rules.refresh}>Refresh rules</Button></div>
        {rules.status === 'loading' && <p role="status">Loading rules…</p>}
        {rules.status === 'error' && <Alert variant="destructive"><AlertDescription>{rules.error}</AlertDescription></Alert>}
        {rules.status === 'ready' && rules.items.length === 0 && <Empty><EmptyHeader><EmptyTitle>No rules on this page</EmptyTitle><EmptyDescription>Add a rule using an existing device UUID.</EmptyDescription></EmptyHeader></Empty>}
        {rules.status === 'ready' && rules.items.map((rule) => <Card key={rule.ruleId}>
          <CardHeader><CardTitle>Run for duration</CardTitle><CardDescription className="break-all">Device: {rule.deviceId}</CardDescription></CardHeader>
          <CardContent className="flex flex-col items-start gap-2"><Badge variant={rule.enabled ? 'default' : 'secondary'}>{rule.enabled ? 'Enabled' : 'Disabled'}</Badge><p>Maximum: {rule.maxDurationSeconds}s · Cooldown: {rule.cooldownSeconds}s</p></CardContent>
          <CardFooter className="flex gap-2"><Button variant="outline" disabled={busy} onClick={() => edit(rule)}>Edit</Button><Button variant="destructive" disabled={busy} onClick={() => setConfirmation({ title: 'Delete safety rule?', description: `Device ${rule.deviceId} will no longer have this rule. New approvals will be blocked until a rule is restored.`, run: async () => { await safetyApi.deleteRule(rule.ruleId); return 'Rule deleted.' } })}>Delete</Button></CardFooter>
        </Card>)}
      </CardContent>
      <CardFooter className="flex gap-3"><Button variant="outline" disabled={busy || rules.status === 'loading' || rules.offset === 0} onClick={() => rules.page(rules.offset - 20)}>Previous</Button><span>Page {rules.offset / 20 + 1}</span><Button variant="outline" disabled={busy || rules.status !== 'ready' || rules.items.length < 20} onClick={() => rules.page(rules.offset + 20)}>Next</Button></CardFooter>
    </Card>
    <Dialog open={editing !== null} onOpenChange={(open) => { if (!open && !busy) setEditing(null) }}><DialogContent><DialogHeader><DialogTitle>{editing === 'new' ? 'New safety rule' : 'Edit safety rule'}</DialogTitle><DialogDescription>Use an existing device UUID. Limits are in seconds. New rules start disabled.</DialogDescription></DialogHeader>
      <form onSubmit={submit}><FieldSet disabled={busy}><FieldGroup>
        <Field><FieldLabel htmlFor="device-id">Device UUID</FieldLabel><Input id="device-id" required pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}" value={form.deviceId} onChange={(e) => setForm({ ...form, deviceId: e.target.value.trim() })} /></Field>
        <Field><FieldLabel htmlFor="maximum">Maximum duration (seconds)</FieldLabel><Input id="maximum" type="number" required min={1} max={2147483647} step={1} value={form.maxDurationSeconds} onChange={(e) => setForm({ ...form, maxDurationSeconds: Number(e.target.value) })} /></Field>
        <Field><FieldLabel htmlFor="cooldown">Cooldown (seconds)</FieldLabel><Input id="cooldown" type="number" required min={0} max={2147483647} step={1} value={form.cooldownSeconds} onChange={(e) => setForm({ ...form, cooldownSeconds: Number(e.target.value) })} /></Field>
        <Field><FieldLabel htmlFor="enabled">Enable rule</FieldLabel><input id="enabled" type="checkbox" checked={form.enabled} onChange={(e) => setForm({ ...form, enabled: e.target.checked })} /></Field>
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
      </FieldGroup><DialogFooter><Button type="button" variant="outline" onClick={() => setEditing(null)}>Cancel</Button><Button type="submit">{busy ? 'Saving…' : 'Save rule'}</Button></DialogFooter></FieldSet></form>
    </DialogContent></Dialog>
    <Dialog open={confirmation !== null} onOpenChange={(open) => { if (!open && !busy) setConfirmation(null) }}><DialogContent><DialogHeader><DialogTitle>{confirmation?.title}</DialogTitle><DialogDescription>{confirmation?.description}</DialogDescription></DialogHeader>{error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}<DialogFooter><Button variant="outline" disabled={busy} onClick={() => setConfirmation(null)}>Cancel</Button><Button disabled={busy} onClick={() => { if (confirmation) void perform(confirmation.run) }}>{busy ? 'Saving…' : 'Confirm'}</Button></DialogFooter></DialogContent></Dialog>
  </section>
}
