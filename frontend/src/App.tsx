import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { AgentsPage } from './features/agents/AgentsPage'
import { LoginPage } from './features/auth/LoginPage'
import { useAuth } from './features/auth/useAuth'
import { DevicesPage } from './features/devices/DevicesPage'
import { OverviewPage } from './features/overview/OverviewPage'
import { SchedulesPage } from './features/schedules/SchedulesPage'

export default function App() {
  const auth = useAuth()

  if (auth.status === 'loading') {
    return (
      <main className="auth-gate">
        <h1>Opening your greenhouse…</h1>
        <p role="status">Checking your session and loading your account.</p>
      </main>
    )
  }

  if (auth.status === 'signedOut') return <LoginPage onSignIn={auth.signIn} />

  if (auth.status === 'error' || !auth.user) {
    return (
      <main className="auth-gate">
        <h1>Account unavailable</h1>
        <p role="alert">{auth.error || 'Unable to load your account. Please try again.'}</p>
        <button className="auth-submit" onClick={auth.retry}>Try again</button>
        {auth.logoutError && <p role="alert">{auth.logoutError}</p>}
      </main>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <AppShell
              key={auth.user.id}
              user={auth.user}
              signingOut={auth.signingOut}
              logoutError={auth.logoutError}
              onProfile={auth.updateProfile}
              onDeleted={() => void auth.finishAccountDeletion()}
              onLogout={() => void auth.signOut()}
            />
          }
        >
          <Route index element={<OverviewPage />} />
          <Route path="agents" element={<AgentsPage />} />
          <Route path="schedules" element={<SchedulesPage />} />
          <Route path="devices" element={<DevicesPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
