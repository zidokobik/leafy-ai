import { useState } from 'react'
import { apiConfig } from './api/config'
import { alertApi } from './api/leafyApi'
import { AppSidebar } from './components/AppSidebar'
import { Topbar } from './components/Topbar'
import { AlertPanel } from './features/alerts/AlertPanel'
import { LoginPage } from './features/auth/LoginPage'
import { useAuth, type Profile } from './features/auth/useAuth'
import { AccountSettings } from './features/auth/AccountSettings'
import { EcDosePanel } from './features/ec-dose/EcDosePanel'
import { MonitoringSection } from './features/monitoring/MonitoringSection'
import { HealthOverview } from './features/overview/HealthOverview'
import { WelcomePanel } from './features/overview/WelcomePanel'
import { ScheduleWorkspace } from './features/schedule/ScheduleWorkspace'
import type { AlertDecision } from './types/dashboard'
import './App.css'

function App() {
  const auth = useAuth()
  if (auth.status === 'loading') {
    return <main className="auth-gate">
      <h1>Opening your greenhouse…</h1>
      <p role="status">Checking your session and loading your account.</p>
    </main>
  }
  if (auth.status === 'signedOut') return <LoginPage onSignIn={auth.signIn} />
  if (auth.status === 'error' || !auth.user) {
    return <main className="auth-gate">
      <h1>Account unavailable</h1>
      <p role="alert">{auth.error || 'Unable to load your account. Please try again.'}</p>
      <button className="auth-submit" onClick={auth.retry}>Try again</button>
      {auth.logoutError && <p role="alert">{auth.logoutError}</p>}
    </main>
  }
  return <Dashboard key={auth.user.id} signOut={() => void auth.signOut()}
    user={auth.user} onProfile={auth.updateProfile}
    onDeleted={() => void auth.finishAccountDeletion()}
    signingOut={auth.signingOut} logoutError={auth.logoutError} />
}

function Dashboard({ signOut, signingOut, logoutError, user, onProfile, onDeleted }: {
  signOut: () => void; signingOut: boolean; logoutError: string
  user: Profile; onProfile: (user: Profile) => void
  onDeleted: () => void
}) {
  const [accountOpen, setAccountOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [alertDecision, setAlertDecision] = useState<AlertDecision>('pending')

  // Internal app: every signed-in user has full control.
  const canControl = true

  const changeAlertDecision = (nextDecision: AlertDecision) => {
    setAlertDecision(nextDecision)

    if (apiConfig.enabled) {
      void alertApi.setDecision(nextDecision).catch((error: unknown) => {
        console.error('Unable to sync alert decision', error)
      })
    }
  }

  return (
    <div className="app-shell">
      {accountOpen && <AccountSettings user={user} onProfile={onProfile}
        onClose={() => setAccountOpen(false)} onDeleted={onDeleted} />}
      <AppSidebar open={menuOpen} onClose={() => setMenuOpen(false)} displayName={[user.firstName, user.lastName].filter(Boolean).join(' ')}
        onAccount={() => setAccountOpen(true)} onLogout={signOut} signingOut={signingOut} />

      <main>
        <Topbar onOpenMenu={() => setMenuOpen(true)} />
        <div className="dashboard">
          {logoutError && <p className="auth-error" role="alert">{logoutError}</p>}
          <WelcomePanel displayName={[user.firstName, user.lastName].filter(Boolean).join(' ')} />
          <AlertPanel canControl={canControl} decision={alertDecision} onDecision={changeAlertDecision} />
          <HealthOverview />
          <ScheduleWorkspace canControl={canControl} decision={alertDecision} />
          <EcDosePanel canControl={canControl} />
          <MonitoringSection />
        </div>
      </main>
    </div>
  )
}

export default App
