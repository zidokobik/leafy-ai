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
import type { AlertDecision, UserRole } from './types/dashboard'
import './App.css'

function App() {
  const auth = useAuth()
  if (auth.session === null && !auth.error) return <LoginPage />
  if (!auth.user || auth.error) {
    return <main className="auth-gate">
      <h1>{auth.error ? 'Account unavailable' : 'Opening your greenhouse…'}</h1>
      <p role={auth.error ? 'alert' : 'status'}>{auth.error || 'Checking your session and loading your account.'}</p>
      {auth.error && <button className="auth-submit" onClick={auth.session ? auth.retry : () => window.location.reload()}>Try again</button>}
      {auth.session && <button disabled={auth.signingOut} onClick={() => void auth.signOut()}>Sign out</button>}
      {auth.logoutError && <p role="alert">{auth.logoutError}</p>}
    </main>
  }
  const role: UserRole = auth.user.roles.includes('admin') ? 'admin'
    : auth.user.roles.includes('operator') ? 'operator' : 'viewer'
  return <Dashboard key={auth.user.id} role={role} signOut={() => void auth.signOut()}
    user={auth.user} onProfile={auth.updateProfile}
    onDeleted={() => void auth.finishAccountDeletion()}
    signingOut={auth.signingOut} logoutError={auth.logoutError} />
}

function Dashboard({ role, signOut, signingOut, logoutError, user, onProfile, onDeleted }: {
  role: UserRole; signOut: () => void; signingOut: boolean; logoutError: string
  user: Profile; onProfile: (user: Profile) => void
  onDeleted: () => void
}) {
  const [accountOpen, setAccountOpen] = useState(false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [alertDecision, setAlertDecision] = useState<AlertDecision>('pending')

  const canControl = role === 'operator' || role === 'admin'

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
