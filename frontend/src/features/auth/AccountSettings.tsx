import { useState, type FormEvent } from 'react'
import { ApiError, apiRequest } from '../../api/client'
import type { Profile } from './useAuth'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
  FieldLegend,
  FieldSet,
} from '@/components/ui/field'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'

type Props = {
  open: boolean
  user: Profile
  onProfile: (user: Profile) => void
  onClose: () => void
  onDeleted: () => void
}

function errorMessage(error: unknown) {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Your session has expired. Please sign in again.'
    return 'Unable to save this change. Please retry or contact your administrator.'
  }
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}

export function AccountSettings({ open, user, onProfile, onClose, onDeleted }: Props) {
  const [firstName, setFirstName] = useState(user.firstName ?? '')
  const [lastName, setLastName] = useState(user.lastName ?? '')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteEmail, setDeleteEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  async function perform(action: () => Promise<void>) {
    if (busy) return
    setBusy(true)
    setError('')
    setMessage('')
    try { await action() }
    catch (cause) { setError(errorMessage(cause)) }
    finally { setBusy(false) }
  }

  function saveProfile(event: FormEvent) {
    event.preventDefault()
    void perform(async () => {
      const updated = await apiRequest<Profile>('/api/v1/users/me', {
        method: 'PATCH', body: { firstName: firstName.trim() || null, lastName: lastName.trim() || null },
      })
      onProfile(updated)
      setFirstName(updated.firstName ?? '')
      setLastName(updated.lastName ?? '')
      setMessage('Your name has been saved.')
    })
  }

  function changePassword(event: FormEvent) {
    event.preventDefault()
    void perform(async () => {
      if (password !== confirmation) throw new Error('Passwords do not match.')
      await apiRequest<void>('/api/v1/users/me/password', {
        method: 'PUT',
        body: { newPassword: password },
      })
      setPassword('')
      setConfirmation('')
      setMessage('Your password has been updated. Use it the next time you sign in.')
    })
  }

  function deleteAccount(event: FormEvent) {
    event.preventDefault()
    if (deleteEmail !== user.email) return
    void perform(async () => {
      await apiRequest<void>('/api/v1/users/me', { method: 'DELETE' })
      onClose()
      onDeleted()
    })
  }

  return (
    <Dialog open={open} onOpenChange={(nextOpen) => { if (!nextOpen && !busy) onClose() }}>
      <DialogContent className="max-h-[90svh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Account settings</DialogTitle>
          <DialogDescription>{user.email}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-5">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {message && (
            <Alert>
              <AlertDescription>{message}</AlertDescription>
            </Alert>
          )}

          <form onSubmit={saveProfile}>
            <FieldSet disabled={busy}>
              <FieldLegend>Personal details</FieldLegend>
              <FieldDescription>Both names are optional. Leave them blank to display your email instead.</FieldDescription>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="first-name">First name</FieldLabel>
                  <Input id="first-name" autoComplete="given-name" maxLength={100} value={firstName} onChange={(event) => setFirstName(event.target.value)} />
                </Field>
                <Field>
                  <FieldLabel htmlFor="last-name">Last name</FieldLabel>
                  <Input id="last-name" autoComplete="family-name" maxLength={100} value={lastName} onChange={(event) => setLastName(event.target.value)} />
                </Field>
                <Button type="submit">Save name</Button>
              </FieldGroup>
            </FieldSet>
          </form>

          <Separator />

          <form onSubmit={changePassword}>
            <FieldSet disabled={busy}>
              <FieldLegend>Change password</FieldLegend>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="new-password">New password</FieldLabel>
                  <Input id="new-password" type="password" required minLength={8} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} />
                  <FieldDescription>Use at least 8 characters.</FieldDescription>
                </Field>
                <Field>
                  <FieldLabel htmlFor="confirm-password">Confirm new password</FieldLabel>
                  <Input id="confirm-password" type="password" required autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
                </Field>
                <Button type="submit">Update password</Button>
              </FieldGroup>
            </FieldSet>
          </form>

          <Separator />

          <FieldSet disabled={busy}>
            <FieldLegend>Delete account</FieldLegend>
            <FieldDescription>Permanently delete your account and profile. This cannot be undone.</FieldDescription>
            {!confirmDelete ? (
              <Button type="button" variant="destructive" onClick={() => setConfirmDelete(true)}>Delete my account</Button>
            ) : (
              <form onSubmit={deleteAccount}>
                <FieldGroup>
                  <Field>
                    <FieldLabel htmlFor="delete-email">Type {user.email} to confirm deletion</FieldLabel>
                    <Input id="delete-email" type="email" required value={deleteEmail} onChange={(event) => setDeleteEmail(event.target.value)} />
                  </Field>
                  <div className="flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
                    <Button type="button" variant="outline" onClick={() => { setConfirmDelete(false); setDeleteEmail('') }}>Cancel</Button>
                    <Button type="submit" variant="destructive" disabled={deleteEmail !== user.email}>Permanently delete account</Button>
                  </div>
                </FieldGroup>
              </form>
            )}
          </FieldSet>

          {busy && <p className="text-sm text-muted-foreground" role="status">Saving your changes...</p>}
        </div>
      </DialogContent>
    </Dialog>
  )
}
