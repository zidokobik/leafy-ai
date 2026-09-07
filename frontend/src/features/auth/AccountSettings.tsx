import { useEffect, useRef, useState, type FormEvent } from 'react'
import { supabase } from '../../Supabase'
import { ApiError, apiRequest } from '../../api/client'
import type { Profile } from './useAuth'
import './AccountSettings.css'

type Props = {
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

export function AccountSettings({ user, onProfile, onClose, onDeleted }: Props) {
  const dialog = useRef<HTMLDialogElement>(null)
  const [firstName, setFirstName] = useState(user.firstName ?? '')
  const [lastName, setLastName] = useState(user.lastName ?? '')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [nonce, setNonce] = useState('')
  const [needsCode, setNeedsCode] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const [deleteEmail, setDeleteEmail] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const element = dialog.current
    const previous = document.activeElement as HTMLElement | null
    element?.showModal()
    return () => { element?.close(); previous?.focus() }
  }, [])

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
      const { error: updateError } = await supabase.auth.updateUser({ password, ...(needsCode ? { nonce: nonce.trim() } : {}) })
      if (updateError) {
        if (updateError.code === 'reauthentication_needed') {
          setNeedsCode(true)
          const { error: codeError } = await supabase.auth.reauthenticate()
          if (codeError) throw codeError
          setMessage('Check your email for a security code, then enter it below to finish changing your password.')
          return
        }
        throw updateError
      }
      setPassword('')
      setConfirmation('')
      setNonce('')
      setNeedsCode(false)
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

  return <dialog className="account-dialog" ref={dialog} aria-labelledby="account-title"
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose() }}>
    <header className="account-heading">
      <div><h1 id="account-title">Account settings</h1><p>{user.email}</p></div>
      <button type="button" disabled={busy} onClick={onClose} aria-label="Close account settings">Close</button>
    </header>
    {error && <p className="auth-error" role="alert">{error}</p>}
    {message && <p className="auth-message" role="status">{message}</p>}
    <form onSubmit={saveProfile}>
      <fieldset disabled={busy}>
        <legend>Personal details</legend>
        <p>Both names are optional. Leave them blank to display your email instead.</p>
        <label htmlFor="first-name">First name</label>
        <input id="first-name" autoComplete="given-name" maxLength={100} value={firstName} onChange={(event) => setFirstName(event.target.value)} />
        <label htmlFor="last-name">Last name</label>
        <input id="last-name" autoComplete="family-name" maxLength={100} value={lastName} onChange={(event) => setLastName(event.target.value)} />
        <button className="auth-submit" type="submit">Save name</button>
      </fieldset>
    </form>
    <form onSubmit={changePassword}>
      <fieldset disabled={busy}>
        <legend>Change password</legend>
        <label htmlFor="new-password">New password</label>
        <input id="new-password" type="password" required minLength={8} autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} />
        <small>Use at least 8 characters.</small>
        <label htmlFor="confirm-password">Confirm new password</label>
        <input id="confirm-password" type="password" required autoComplete="new-password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />
        {needsCode && <>
          <label htmlFor="security-code">Email security code</label>
          <input id="security-code" required autoComplete="one-time-code" value={nonce} onChange={(event) => setNonce(event.target.value)} />
          <button type="button" onClick={() => void perform(async () => {
            const { error: codeError } = await supabase.auth.reauthenticate()
            if (codeError) throw codeError
            setMessage('A new security code has been sent to your email.')
          })}>Send another code</button>
        </>}
        <button className="auth-submit" type="submit">Update password</button>
      </fieldset>
    </form>
    <section className="account-danger" aria-labelledby="delete-title">
      <h2 id="delete-title">Delete account</h2>
      <p>Permanently delete your account, profile and assigned roles. This cannot be undone.</p>
      {!confirmDelete ? <button type="button" disabled={busy} onClick={() => setConfirmDelete(true)}>Delete my account</button>
        : <form onSubmit={deleteAccount}>
          <fieldset disabled={busy}>
            <label htmlFor="delete-email">Type {user.email} to confirm deletion</label>
            <input id="delete-email" type="email" required value={deleteEmail} onChange={(event) => setDeleteEmail(event.target.value)} />
            <button className="delete-confirm" type="submit" disabled={deleteEmail !== user.email}>Permanently delete account</button>
            <button type="button" onClick={() => { setConfirmDelete(false); setDeleteEmail('') }}>Cancel</button>
          </fieldset>
        </form>}
    </section>
    {busy && <p role="status">Saving your changes…</p>}
  </dialog>
}
