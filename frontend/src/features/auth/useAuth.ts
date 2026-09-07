import { useEffect, useState } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../../Supabase'
import { ApiError, apiRequest } from '../../api/client'

export type Profile = {
  id: string; email: string; roles: string[]
  firstName: string | null; lastName: string | null
}

export function useAuth() {
  const [session, setSession] = useState<Session | null | undefined>(undefined)
  const [profile, setProfile] = useState<{ token: string; user: Profile } | null>(null)
  const [failure, setFailure] = useState<{ token: string; message: string } | null>(null)
  const [sessionError, setSessionError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [signingOut, setSigningOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')
  const token = session?.access_token
  const userId = session?.user.id

  useEffect(() => {
    // Keep the callback synchronous to avoid holding the SDK auth lock.
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next)
      setSessionError('')
      setLogoutError('')
      if (!next) { setProfile(null); setFailure(null) }
    })
    let active = true
    void supabase.auth.initialize().then(({ error }) => {
      if (active && error) {
        setSessionError('Unable to restore your session. Please reload and try again.')
        setSession(null)
      }
    }).catch(() => {
      if (active) { setSessionError('Unable to connect. Please reload and try again.'); setSession(null) }
    })
    return () => { active = false; subscription.unsubscribe() }
  }, [])

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    void apiRequest<Profile>('/api/v1/users/me', {
      headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
    }).then((user) => {
      if (controller.signal.aborted) return
      if (user.id !== userId || !Array.isArray(user.roles)) throw new Error('Invalid profile response')
      setProfile({ token, user })
      setFailure(null)
    }).catch((error: unknown) => {
      if (controller.signal.aborted) return
      let message = 'Unable to load your account. Please try again.'
      if (error instanceof ApiError && error.status === 401) message = 'Your session could not be verified. Please sign out and sign in again.'
      if (error instanceof ApiError && error.status === 404) message = 'Your account profile is not ready. Please retry or contact your administrator.'
      setFailure({ token, message })
    })
    return () => controller.abort()
  }, [token, userId, attempt])

  async function signOut() {
    if (signingOut) return
    setSigningOut(true)
    setLogoutError('')
    try {
      const { error } = await supabase.auth.signOut({ scope: 'local' })
      if (error) throw error
      setSession(null)
      setProfile(null)
      setFailure(null)
    } catch { setLogoutError('Unable to sign out. Please try again.') }
    finally { setSigningOut(false) }
  }

  return {
    session, user: profile?.user.id === userId ? profile?.user : undefined,
    error: failure && failure.token === token ? failure.message : sessionError,
    signingOut, logoutError, signOut,
    finishAccountDeletion: async () => {
      await signOut()
      // Auth deletion is already confirmed: never keep the deleted profile on screen.
      setSession(null)
      setProfile(null)
      setFailure(null)
      setSessionError('')
    },
    updateProfile: (user: Profile) => {
      if (token && user.id === userId) setProfile({ token, user })
    },
    retry: () => { setFailure(null); setAttempt((value) => value + 1) },
  }
}
