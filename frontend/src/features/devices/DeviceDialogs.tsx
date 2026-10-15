import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Field, FieldDescription, FieldError, FieldGroup, FieldLabel, FieldSet } from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectGroup, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { errorDetail } from '../../api/client'
import {
  devicesApi,
  type DeviceType,
  type FarmDevice,
  type Powerboard,
  type PowerboardState,
} from '../../api/devices'
import { deviceTypes } from './deviceTypes'

type DialogProps = {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSaved: () => void
}

/** Add or edit a powerboard. Remount it (change its key) for each opening so the form starts fresh. */
export function PowerboardFormDialog({ open, onOpenChange, onSaved, powerboard }: DialogProps & {
  powerboard: Powerboard | null
}) {
  const [name, setName] = useState(powerboard?.name ?? '')
  const [host, setHost] = useState(powerboard?.host ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const body = { name: name.trim(), host: host.trim() }
      if (powerboard) await devicesApi.updatePowerboard(powerboard.id, body)
      else await devicesApi.createPowerboard(body)
      onSaved()
      onOpenChange(false)
    } catch (cause) {
      setError(errorDetail(cause, 'Unable to save. Check the name and host, then try again.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!saving) onOpenChange(next) }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{powerboard ? 'Edit powerboard' : 'Add powerboard'}</DialogTitle>
          <DialogDescription>A Kasa power strip on the same network as the Leafy server.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <FieldSet disabled={saving}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="powerboard-name">Name</FieldLabel>
                <Input
                  id="powerboard-name"
                  required
                  maxLength={100}
                  placeholder="Rack 1 powerboard"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
              <Field data-invalid={Boolean(error)}>
                <FieldLabel htmlFor="powerboard-host">Host</FieldLabel>
                <Input
                  id="powerboard-host"
                  required
                  maxLength={255}
                  pattern="[A-Za-z0-9.\-]+"
                  placeholder="192.168.1.101"
                  value={host}
                  aria-invalid={Boolean(error)}
                  onChange={(event) => setHost(event.target.value)}
                />
                <FieldDescription>
                  Its IP address or hostname, without http:// or a port. Reserve the IP in your router so it
                  does not change.
                </FieldDescription>
                {error && <FieldError>{error}</FieldError>}
              </Field>
            </FieldGroup>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit">{saving ? 'Saving…' : powerboard ? 'Save changes' : 'Add powerboard'}</Button>
            </DialogFooter>
          </FieldSet>
        </form>
      </DialogContent>
    </Dialog>
  )
}

/** Add or edit a device. Remount it (change its key) for each opening so the form starts fresh. */
export function DeviceFormDialog({ open, onOpenChange, onSaved, device, powerboards, states }: DialogProps & {
  device: FarmDevice | null
  powerboards: Powerboard[]
  states: Record<string, PowerboardState>
}) {
  const [name, setName] = useState(device?.name ?? '')
  const [deviceType, setDeviceType] = useState<DeviceType | ''>(device?.deviceType ?? '')
  const [powerboardId, setPowerboardId] = useState(device?.powerboardId ?? '')
  const [outletNum, setOutletNum] = useState(device ? String(device.outletNum) : '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  // Derived at render: the powerboards may still be loading when the dialog first mounts.
  const boardId = powerboardId || powerboards[0]?.id || ''
  const outletCount = states[boardId]?.outlets?.length

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!deviceType || !boardId) {
      setError('Choose a device type and a powerboard.')
      return
    }
    setSaving(true)
    setError('')
    try {
      const body = { name: name.trim(), deviceType, powerboardId: boardId, outletNum: Number(outletNum) }
      if (device) await devicesApi.update(device.id, body)
      else await devicesApi.create(body)
      onSaved()
      onOpenChange(false)
    } catch (cause) {
      setError(errorDetail(cause, 'Unable to save the device. Check the fields, then try again.'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={(next) => { if (!saving) onOpenChange(next) }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{device ? 'Edit device' : 'Add device'}</DialogTitle>
          <DialogDescription>Equipment plugged into one outlet of a powerboard.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit}>
          <FieldSet disabled={saving}>
            <FieldGroup>
              <Field>
                <FieldLabel htmlFor="device-name">Name</FieldLabel>
                <Input
                  id="device-name"
                  required
                  maxLength={100}
                  placeholder="Circulation fan"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                />
              </Field>
              <Field>
                <FieldLabel htmlFor="device-type">Type</FieldLabel>
                <Select value={deviceType} onValueChange={(value) => setDeviceType(value as DeviceType)}>
                  <SelectTrigger id="device-type" className="w-full">
                    <SelectValue placeholder="Choose a type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {deviceTypes.map(({ value, label }) => (
                        <SelectItem key={value} value={value}>{label}</SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
              <Field>
                <FieldLabel htmlFor="device-powerboard">Powerboard</FieldLabel>
                <Select value={boardId} onValueChange={setPowerboardId}>
                  <SelectTrigger id="device-powerboard" className="w-full">
                    <SelectValue placeholder="Choose a powerboard" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectGroup>
                      {powerboards.map((powerboard) => (
                        <SelectItem key={powerboard.id} value={powerboard.id}>
                          {powerboard.name} ({powerboard.host})
                        </SelectItem>
                      ))}
                    </SelectGroup>
                  </SelectContent>
                </Select>
              </Field>
              <Field data-invalid={Boolean(error)}>
                <FieldLabel htmlFor="device-outlet">Outlet number</FieldLabel>
                <Input
                  id="device-outlet"
                  type="number"
                  required
                  min={1}
                  max={outletCount ?? 64}
                  step={1}
                  value={outletNum}
                  aria-invalid={Boolean(error)}
                  onChange={(event) => setOutletNum(event.target.value)}
                />
                <FieldDescription>
                  {outletCount ? `This powerboard has ${outletCount} outlets. ` : ''}
                  Outlet 1 is the first socket on the powerboard (Plug 1 in the Kasa app).
                </FieldDescription>
                {error && <FieldError>{error}</FieldError>}
              </Field>
            </FieldGroup>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
              <Button type="submit">{saving ? 'Saving…' : device ? 'Save changes' : 'Add device'}</Button>
            </DialogFooter>
          </FieldSet>
        </form>
      </DialogContent>
    </Dialog>
  )
}
