import { useState, type FormEvent } from 'react'
import leafyLogo from '../../assets/Leafy_AI_logo.png'
import { supabase } from '../../Supabase'
import './LoginPage.css'

export function LoginPage() {
  const [mode, setMode] = useState<'login' | 'signup'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const signup = mode === 'signup'

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setError('')
    setMessage('')
    if (signup && password !== confirmation) { setError('Passwords do not match.'); return }
    setBusy(true)
    try {
      const credentials = { email: email.trim(), password }
      const { data, error: authError } = signup
        ? await supabase.auth.signUp({ ...credentials, options: { emailRedirectTo: window.location.origin } })
        : await supabase.auth.signInWithPassword(credentials)
      if (authError) {
        if (authError.code === 'invalid_credentials') throw new Error('The email or password is incorrect.')
        if (authError.code === 'email_not_confirmed') throw new Error('Please verify your email before signing in.')
        if (authError.status === 429) throw new Error('Too many attempts. Please wait a moment and try again.')
        throw authError
      }
      setPassword('')
      setConfirmation('')
      if (signup && !data.session) {
        setMessage('Check your inbox for a confirmation link. Once your email is verified, sign in to continue. If you already have an account, sign in instead.')
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Unable to connect. Please try again.')
    } finally { setBusy(false) }
  }

  return (
    <main className="login-shell">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-brand"><img src={leafyLogo} alt="Leafy AI" /></div>
        <div className="login-copy">
          <span className="login-kicker">Your greenhouse, connected</span>
          <h1 id="login-title">{signup ? 'Start growing with us.' : 'Welcome back.'}</h1>
          <p>{signup ? 'Create an account to stay connected to your greenhouse.' : 'Sign in to see your greenhouse and keep track of every growing day.'}</p>
        </div>
        <div className="auth-switch" aria-label="Account access">
          {(['login', 'signup'] as const).map((value) => (
            <button key={value} type="button" aria-pressed={mode === value} disabled={busy}
              onClick={() => { setMode(value); setError(''); setMessage(''); setPassword(''); setConfirmation('') }}>
              {value === 'login' ? 'Sign in' : 'Create account'}
            </button>
          ))}
        </div>
        <form className="auth-form" onSubmit={submit} aria-busy={busy}>
          <label htmlFor="auth-email">Email</label>
          <input id="auth-email" type="email" autoComplete="email" required maxLength={254} value={email}
            disabled={busy} onChange={(event) => setEmail(event.target.value)} />
          <label htmlFor="auth-password">Password</label>
          <input id="auth-password" type="password" autoComplete={signup ? 'new-password' : 'current-password'}
            required minLength={signup ? 8 : undefined} value={password} disabled={busy}
            aria-describedby={signup ? 'password-help' : undefined} onChange={(event) => setPassword(event.target.value)} />
          {signup && <>
            <small id="password-help">Use at least 8 characters.</small>
            <label htmlFor="auth-confirm">Confirm password</label>
            <input id="auth-confirm" type="password" autoComplete="new-password" required value={confirmation}
              disabled={busy} onChange={(event) => setConfirmation(event.target.value)} />
          </>}
          {error && <p className="auth-error" role="alert">{error}</p>}
          {message && <p className="auth-message" role="status">{message}</p>}
          <button className="auth-submit" disabled={busy} type="submit">
            {busy ? 'Please wait…' : signup ? 'Create account' : 'Sign in'}
          </button>
        </form>
      </section>
      <aside className="login-visual" aria-label="Leafy greenhouse">
        <div className="login-visual-mark"><img src={leafyLogo} alt="Leafy AI" /></div>
        <div><span>Grow with confidence</span><h2>One view for every growing decision.</h2>
          <p>Your plants, growing conditions and daily insights, all in one place.</p></div>
        <div className="login-status">A little care. A greener tomorrow.</div>
      </aside>
    </main>
  )
}
