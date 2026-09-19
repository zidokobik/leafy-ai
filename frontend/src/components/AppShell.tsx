import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { AccountSettings } from '../features/auth/AccountSettings'
import type { Profile } from '../features/auth/useAuth'
import { AppSidebar } from './AppSidebar'
import { Topbar } from './Topbar'

type AppShellProps = {
  user: Profile
  signingOut: boolean
  logoutError: string
  onProfile: (user: Profile) => void
  onDeleted: () => void
  onLogout: () => void
}

export function AppShell({ user, signingOut, logoutError, onProfile, onDeleted, onLogout }: AppShellProps) {
  const [menuOpen, setMenuOpen] = useState(false)
  const [accountOpen, setAccountOpen] = useState(false)
  const displayName = [user.firstName, user.lastName].filter(Boolean).join(' ') || user.email

  return (
    <div className="app-shell">
      {accountOpen && (
        <AccountSettings
          user={user}
          onProfile={onProfile}
          onClose={() => setAccountOpen(false)}
          onDeleted={onDeleted}
        />
      )}

      <AppSidebar
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        displayName={displayName}
        onAccount={() => setAccountOpen(true)}
        onLogout={onLogout}
        signingOut={signingOut}
      />

      <main>
        <Topbar onOpenMenu={() => setMenuOpen(true)} />
        <div className="page">
          {logoutError && <p className="auth-error" role="alert">{logoutError}</p>}
          <Outlet />
        </div>
      </main>
    </div>
  )
}
