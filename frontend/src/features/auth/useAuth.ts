import { useEffect, useState } from 'react'
import { ApiError, apiRequest } from '../../api/client'

export type Profile = {
  id: string; email: string
  firstName: string | null; lastName: string | null
}

type Status = 'loading' | 'signedOut' | 'signedIn' | 'error'

export function useAuth() {
  const [status, setStatus] = useState<Status>('loading')
  const [user, setUser] = useState<Profile | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [signingOut, setSigningOut] = useState(false)
  const [logoutError, setLogoutError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    void apiRequest<Profile>('/api/v1/users/me', { signal: controller.signal })
      .then((profile) => {
        if (controller.signal.aborted) return
        setUser(profile)
        setStatus('signedIn')
        setError('')
      })
      .catch((cause: unknown) => {
        if (controller.signal.aborted) return
        if (cause instanceof ApiError && cause.status === 401) {
          setStatus('signedOut')
          return
        }
        setError('Unable to load your account. Please try again.')
        setStatus('error')
      })
    return () => controller.abort()
  }, [attempt])

  async function signIn(email: string, password: string) {
    const profile = await apiRequest<Profile>('/api/v1/auth/login', {
      method: 'POST',
      body: { email, password },
    })
    setUser(profile)
    setStatus('signedIn')
    setError('')
  }

  async function signOut() {
    if (signingOut) return
    setSigningOut(true)
    setLogoutError('')
    try {
      await apiRequest<void>('/api/v1/auth/logout', { method: 'POST' })
      setUser(null)
      setStatus('signedOut')
    } catch {
      setLogoutError('Unable to sign out. Please try again.')
    } finally {
      setSigningOut(false)
    }
  }

  return {
    status,
    user: status === 'signedIn' && user ? user : undefined,
    error,
    signingOut,
    logoutError,
    signIn,
    signOut,
    finishAccountDeletion: async () => {
      await signOut()
    },
    updateProfile: (next: Profile) => setUser(next),
    retry: () => { setError(''); setStatus('loading'); setAttempt((value) => value + 1) },
  }
}
