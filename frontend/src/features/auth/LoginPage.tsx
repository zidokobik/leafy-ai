import { useState, type FormEvent } from 'react'
import leafyLogo from '../../assets/Leafy_AI_logo.png'
import { ApiError } from '../../api/client'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Field, FieldGroup, FieldLabel } from '@/components/ui/field'
import { Input } from '@/components/ui/input'

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
    <main className="grid min-h-svh bg-background lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.78fr)]">
      <section className="flex items-center justify-center p-6 md:p-10" aria-labelledby="login-title">
        <Card className="w-full max-w-md">
          <CardHeader>
            <img className="mb-8 h-10 w-fit" src={leafyLogo} alt="Leafy AI" />
            <CardDescription>Your greenhouse, connected</CardDescription>
            <CardTitle id="login-title" className="text-3xl">Welcome back.</CardTitle>
            <CardDescription>Sign in to see your greenhouse and keep track of every growing day.</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={submit} aria-busy={busy}>
              <FieldGroup>
                <Field>
                  <FieldLabel htmlFor="auth-email">Email</FieldLabel>
                  <Input
                    id="auth-email"
                    type="email"
                    autoComplete="email"
                    required
                    maxLength={254}
                    value={email}
                    disabled={busy}
                    onChange={(event) => setEmail(event.target.value)}
                  />
                </Field>
                <Field>
                  <FieldLabel htmlFor="auth-password">Password</FieldLabel>
                  <Input
                    id="auth-password"
                    type="password"
                    autoComplete="current-password"
                    required
                    value={password}
                    disabled={busy}
                    onChange={(event) => setPassword(event.target.value)}
                  />
                </Field>
                {error && (
                  <Alert variant="destructive">
                    <AlertDescription>{error}</AlertDescription>
                  </Alert>
                )}
                <Button disabled={busy} type="submit" className="w-full">
                  {busy ? 'Please wait...' : 'Sign in'}
                </Button>
              </FieldGroup>
            </form>
          </CardContent>
        </Card>
      </section>
      <aside className="hidden min-h-[calc(100svh-2rem)] flex-col justify-between overflow-hidden rounded-xl bg-sidebar p-10 text-sidebar-foreground ring-1 ring-sidebar-border lg:my-4 lg:mr-4 lg:flex" aria-label="Leafy greenhouse">
        <Card className="w-fit bg-background/95">
          <CardContent className="p-3">
            <img className="h-10 w-auto" src={leafyLogo} alt="Leafy AI" />
          </CardContent>
        </Card>
        <div className="max-w-md">
          <p className="text-sm font-medium text-sidebar-foreground/70">Grow with confidence</p>
          <h2 className="mt-3 text-4xl font-medium tracking-tight">One view for every growing decision.</h2>
          <p className="mt-4 text-sm leading-6 text-sidebar-foreground/70">Your plants, growing conditions and daily insights, all in one place.</p>
        </div>
        <p className="text-sm font-medium text-sidebar-foreground/70">A little care. A greener tomorrow.</p>
      </aside>
    </main>
  )
}
