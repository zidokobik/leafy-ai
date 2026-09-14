import { useState, type FormEvent } from 'react'
import leafyLogo from '../../assets/Leafy_AI_logo.png'
import { ApiError } from '../../api/client'
import './LoginPage.css'

type Props = {
  onSignIn: (email: string, password: string) => Promise<void>
}

export function LoginPage({ onSignIn }: Props) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setError('')
    setBusy(true)
    try {
      await onSignIn(email.trim(), password)
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 401) setError('The email or password is incorrect.')
      else if (cause instanceof ApiError && cause.status === 429) setError('Too many attempts. Please wait a moment and try again.')
      else setError(cause instanceof Error ? cause.message : 'Unable to connect. Please try again.')
    } finally { setBusy(false) }
  }

  return (
    <main className="login-shell">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-brand"><img src={leafyLogo} alt="Leafy AI" /></div>
        <div className="login-copy">
          <span className="login-kicker">Your greenhouse, connected</span>
          <h1 id="login-title">Welcome back.</h1>
          <p>Sign in to see your greenhouse and keep track of every growing day.</p>
        </div>
        <form className="auth-form" onSubmit={submit} aria-busy={busy}>
          <label htmlFor="auth-email">Email</label>
          <input id="auth-email" type="email" autoComplete="email" required maxLength={254} value={email}
            disabled={busy} onChange={(event) => setEmail(event.target.value)} />
          <label htmlFor="auth-password">Password</label>
          <input id="auth-password" type="password" autoComplete="current-password"
            required value={password} disabled={busy} onChange={(event) => setPassword(event.target.value)} />
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" disabled={busy} type="submit">
            {busy ? 'Please wait…' : 'Sign in'}
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
