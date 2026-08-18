import { useState } from 'react'
import { apiConfig } from './api/config'
import { alertApi } from './api/leafyApi'
import { AppSidebar } from './components/AppSidebar'
import { Topbar } from './components/Topbar'
import { AlertPanel } from './features/alerts/AlertPanel'
import { LoginPage } from './features/auth/LoginPage'
import { EcDosePanel } from './features/ec-dose/EcDosePanel'
import { MonitoringSection } from './features/monitoring/MonitoringSection'
import { HealthOverview } from './features/overview/HealthOverview'
import { WelcomePanel } from './features/overview/WelcomePanel'
import { ScheduleWorkspace } from './features/schedule/ScheduleWorkspace'
import type { AlertDecision, UserRole } from './types/dashboard'
import './App.css'

function App() {
  const [role, setRole] = useState<UserRole | null>(() => {
    const storedRole = window.sessionStorage.getItem('leafy-demo-role')
    return storedRole === 'viewer' || storedRole === 'operator' ? storedRole : null
  })
  const [menuOpen, setMenuOpen] = useState(false)
  const [alertDecision, setAlertDecision] = useState<AlertDecision>('pending')

  if (!role) {
    return (
      <LoginPage
        onLogin={(nextRole) => {
          window.sessionStorage.setItem('leafy-demo-role', nextRole)
          setRole(nextRole)
        }}
      />
    )
  }

  const canControl = role === 'operator'

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
      <AppSidebar open={menuOpen} onClose={() => setMenuOpen(false)} />

      <main>
        <Topbar
          role={role}
          onLogout={() => {
            window.sessionStorage.removeItem('leafy-demo-role')
            window.history.replaceState(null, '', window.location.pathname)
            setRole(null)
          }}
          onOpenMenu={() => setMenuOpen(true)}
        />
        <div className="dashboard">
          <WelcomePanel />
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
