import { useState } from 'react'
import {
  CircleAlertIcon,
  PencilIcon,
  PlugZapIcon,
  PlusIcon,
  PowerIcon,
  RefreshCwIcon,
  Trash2Icon,
} from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { errorDetail } from '../../api/client'
import { devicesApi, type FarmDevice, type Powerboard, type PowerboardState } from '../../api/devices'
import type { DeviceProposal } from '../../api/proposals'
import { openStatuses, proposalTime } from '../proposals/proposalMeta'
import { useProposals } from '../proposals/useProposals'
import { DeviceFormDialog, PowerboardFormDialog } from './DeviceDialogs'
import { deviceTypeMeta } from './deviceTypes'
import { useDevicesData } from './useDevicesData'

type Deletion = { kind: 'device', item: FarmDevice } | { kind: 'powerboard', item: Powerboard }

/** The outlet's on/off state, or null when it is unknown (board unread, unreachable or missing the outlet). */
function outletOn(device: FarmDevice, state?: PowerboardState) {
  return state?.outlets?.[device.outletNum - 1] ?? null
}

function OutletState({ device, state, checking }: { device: FarmDevice, state?: PowerboardState, checking: boolean }) {
  if (!state) return checking ? <Badge variant="outline">Checking…</Badge> : null
  if (!state.outlets) return <Badge variant="destructive" title={state.error ?? undefined}>Unreachable</Badge>
  if (device.outletNum > state.outlets.length) {
    return <Badge variant="destructive">No outlet {device.outletNum} on this powerboard</Badge>
  }
  return state.outlets[device.outletNum - 1] ? <Badge>On</Badge> : <Badge variant="secondary">Off</Badge>
}

function OpenProposalBadge({ proposal }: { proposal?: DeviceProposal }) {
  if (proposal?.status === 'running' && proposal.endsAt) {
    return <Badge variant="outline">Agent run until {proposalTime.format(Date.parse(proposal.endsAt))}</Badge>
  }
  if (proposal?.status === 'pending') return <Badge variant="outline">Proposal awaiting review</Badge>
  return null
}

function PowerboardStatus({ state, checking }: { state?: PowerboardState, checking: boolean }) {
  if (!state) return checking ? <Badge variant="outline">Checking…</Badge> : null
  if (!state.outlets) return <Badge variant="destructive">Unreachable</Badge>
  return <Badge variant="secondary">Online · {state.outlets.length} outlets</Badge>
}

export function DevicesPage() {
  const {
    powerboards,
    devices,
    status,
    error,
    states,
    statesStatus,
    statesError,
    refresh,
    refreshStates,
    setOutletState,
  } = useDevicesData()
  const { proposals: openProposals, refresh: refreshProposals } = useProposals({ statuses: openStatuses })
  // Dialogs remount (new key) on every opening so their forms start from the selected record.
  const [deviceDialog, setDeviceDialog] = useState({ key: 0, open: false, device: null as FarmDevice | null })
  const [boardDialog, setBoardDialog] = useState({ key: 0, open: false, powerboard: null as Powerboard | null })
  const [deletion, setDeletion] = useState<Deletion | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')
  // Kept after closing so the dialog does not change text while it animates out.
  const [turnOnDialog, setTurnOnDialog] = useState({ open: false, device: null as FarmDevice | null })
  const [switchingId, setSwitchingId] = useState<string | null>(null)
  const [switchError, setSwitchError] = useState('')
  const checking = statesStatus === 'loading'
  const boardNames = Object.fromEntries(powerboards.map((powerboard) => [powerboard.id, powerboard.name]))
  const openByDevice = Object.fromEntries(openProposals.map((proposal) => [proposal.deviceId, proposal]))

  async function switchDevice(device: FarmDevice, on: boolean) {
    setSwitchingId(device.id)
    setSwitchError('')
    try {
      if (on) await devicesApi.turnOn(device.id)
      else await devicesApi.turnOff(device.id)
      if (states[device.powerboardId]?.outlets) setOutletState(device.powerboardId, device.outletNum, on)
      else refreshStates()
    } catch (cause) {
      setSwitchError(`Could not switch ${device.name} ${on ? 'on' : 'off'}. ${errorDetail(cause, 'Refresh and try again.')}`)
    } finally {
      setSwitchingId(null)
      setTurnOnDialog((current) => ({ ...current, open: false }))
      // Switching off may have stopped an agent run.
      if (!on) refreshProposals()
    }
  }

  function openDeviceDialog(device: FarmDevice | null) {
    setDeviceDialog((current) => ({ key: current.key + 1, open: true, device }))
  }

  function openBoardDialog(powerboard: Powerboard | null) {
    setBoardDialog((current) => ({ key: current.key + 1, open: true, powerboard }))
  }

  function requestDeletion(next: Deletion) {
    setDeleteError('')
    setDeletion(next)
  }

  async function confirmDeletion() {
    if (!deletion) return
    setDeleting(true)
    setDeleteError('')
    try {
      if (deletion.kind === 'device') await devicesApi.remove(deletion.item.id)
      else await devicesApi.deletePowerboard(deletion.item.id)
      setDeletion(null)
      refresh()
    } catch (cause) {
      setDeleteError(errorDetail(cause, 'Unable to delete. Refresh and try again.'))
    } finally {
      setDeleting(false)
    }
  }

  return (
    <section className="mx-auto flex w-full max-w-5xl flex-col gap-6 pb-8">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-medium tracking-tight">Devices</h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Equipment plugged into Kasa powerboards. Switch devices by hand here. The agent can only propose
            timed runs; a person approves each one on the Overview or Logs page, and the device switches off
            by itself when the run ends.
          </p>
        </div>
        <Button type="button" variant="outline" disabled={checking} onClick={refreshStates}>
          <RefreshCwIcon data-icon="inline-start" />
          {checking ? 'Reading powerboards…' : 'Refresh states'}
        </Button>
      </header>

      {(error || statesError) && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertTitle>{error ? 'Devices unavailable' : 'Powerboard states unavailable'}</AlertTitle>
          <AlertDescription>{error || statesError}</AlertDescription>
        </Alert>
      )}
      {switchError && (
        <Alert variant="destructive">
          <CircleAlertIcon />
          <AlertDescription>{switchError}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>Devices</CardTitle>
          <CardDescription>
            Each device is one powerboard outlet. On/off states are read live; a device switched on here stays
            on until switched off.
          </CardDescription>
          <CardAction>
            <Button
              type="button"
              size="sm"
              disabled={powerboards.length === 0}
              title={powerboards.length === 0 ? 'Add a powerboard first' : undefined}
              onClick={() => openDeviceDialog(null)}
            >
              <PlusIcon data-icon="inline-start" />
              Add device
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {status === 'loading' && (
            <>
              <Skeleton className="h-14 w-full" />
              <Skeleton className="h-14 w-full" />
            </>
          )}
          {status !== 'loading' && devices.length === 0 && (
            <Empty>
              <EmptyHeader>
                <EmptyMedia variant="icon">
                  <PlugZapIcon />
                </EmptyMedia>
                <EmptyTitle>No devices yet</EmptyTitle>
                <EmptyDescription>
                  {powerboards.length === 0
                    ? 'Add a powerboard below, then add the equipment plugged into it.'
                    : 'Add the equipment plugged into your powerboards.'}
                </EmptyDescription>
              </EmptyHeader>
            </Empty>
          )}
          {devices.map((device) => {
            const { label, Icon } = deviceTypeMeta[device.deviceType]
            const isOn = outletOn(device, states[device.powerboardId])
            const switching = switchingId === device.id
            return (
              <div key={device.id} className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center">
                <Icon className="size-5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{device.name}</p>
                    <Badge variant="outline">{label}</Badge>
                    {switching
                      ? <Badge variant="outline">Switching…</Badge>
                      : <OutletState device={device} state={states[device.powerboardId]} checking={checking} />}
                    <OpenProposalBadge proposal={openByDevice[device.id]} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {boardNames[device.powerboardId] ?? 'Unknown powerboard'} · outlet {device.outletNum}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Switch
                    checked={isOn === true}
                    disabled={isOn === null || switchingId !== null}
                    aria-label={`${device.name} power`}
                    title={isOn === null ? 'State unknown; refresh the powerboard states' : undefined}
                    onCheckedChange={(checked) => {
                      if (checked) setTurnOnDialog({ open: true, device })
                      else void switchDevice(device, false)
                    }}
                  />
                  <Button type="button" variant="outline" size="sm" onClick={() => openDeviceDialog(device)}>
                    <PencilIcon data-icon="inline-start" />
                    Edit
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => requestDeletion({ kind: 'device', item: device })}
                  >
                    <Trash2Icon data-icon="inline-start" />
                    Delete
                  </Button>
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Powerboards</CardTitle>
          <CardDescription>Kasa power strips the server reaches over the local network.</CardDescription>
          <CardAction>
            <Button type="button" size="sm" variant="outline" onClick={() => openBoardDialog(null)}>
              <PlusIcon data-icon="inline-start" />
              Add powerboard
            </Button>
          </CardAction>
        </CardHeader>
        <CardContent className="flex flex-col gap-3">
          {status === 'loading' && <Skeleton className="h-14 w-full" />}
          {status !== 'loading' && powerboards.length === 0 && (
            <p className="text-sm text-muted-foreground">No powerboards yet.</p>
          )}
          {powerboards.map((powerboard) => {
            const state = states[powerboard.id]
            const deviceCount = devices.filter((device) => device.powerboardId === powerboard.id).length
            return (
              <div key={powerboard.id} className="flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-medium">{powerboard.name}</p>
                    <PowerboardStatus state={state} checking={checking} />
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    <span className="font-mono">{powerboard.host}</span>
                    {' · '}
                    {deviceCount === 1 ? '1 device' : `${deviceCount} devices`}
                  </p>
                  {state?.error && <p className="mt-1 text-sm text-destructive">{state.error}</p>}
                </div>
                <div className="flex shrink-0 gap-2">
                  <Button type="button" variant="outline" size="sm" onClick={() => openBoardDialog(powerboard)}>
                    <PencilIcon data-icon="inline-start" />
                    Edit
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => requestDeletion({ kind: 'powerboard', item: powerboard })}
                  >
                    <Trash2Icon data-icon="inline-start" />
                    Delete
                  </Button>
                </div>
              </div>
            )
          })}
        </CardContent>
      </Card>

      <DeviceFormDialog
        key={`device-${deviceDialog.key}`}
        open={deviceDialog.open}
        device={deviceDialog.device}
        powerboards={powerboards}
        states={states}
        onOpenChange={(open) => setDeviceDialog((current) => ({ ...current, open }))}
        onSaved={refresh}
      />
      <PowerboardFormDialog
        key={`powerboard-${boardDialog.key}`}
        open={boardDialog.open}
        powerboard={boardDialog.powerboard}
        onOpenChange={(open) => setBoardDialog((current) => ({ ...current, open }))}
        onSaved={refresh}
      />

      <Dialog
        open={turnOnDialog.open}
        onOpenChange={(open) => { if (!open && switchingId === null) setTurnOnDialog((current) => ({ ...current, open })) }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Turn on {turnOnDialog.device?.name}?</DialogTitle>
            <DialogDescription>
              It stays on until you turn it off here. To run it for a set time, ask the agent to propose a run
              instead; approved runs switch off by themselves.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={switchingId !== null}
              onClick={() => setTurnOnDialog((current) => ({ ...current, open: false }))}
            >
              Cancel
            </Button>
            <Button
              type="button"
              disabled={switchingId !== null}
              onClick={() => { if (turnOnDialog.device) void switchDevice(turnOnDialog.device, true) }}
            >
              <PowerIcon data-icon="inline-start" />
              {switchingId !== null ? 'Turning on…' : 'Turn on'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deletion !== null} onOpenChange={(open) => { if (!open && !deleting) setDeletion(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete {deletion?.item.name}?</DialogTitle>
            <DialogDescription>
              {deletion?.kind === 'device'
                ? 'Its pending proposal, if any, is rejected. A run in progress still switches off on time.'
                : 'Devices still assigned to this powerboard must be moved or deleted first.'}
            </DialogDescription>
          </DialogHeader>
          {deleteError && (
            <Alert variant="destructive">
              <AlertDescription>{deleteError}</AlertDescription>
            </Alert>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" disabled={deleting} onClick={() => setDeletion(null)}>
              Cancel
            </Button>
            <Button type="button" variant="destructive" disabled={deleting} onClick={() => void confirmDeletion()}>
              <Trash2Icon data-icon="inline-start" />
              {deleting ? 'Deleting…' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </section>
  )
}
