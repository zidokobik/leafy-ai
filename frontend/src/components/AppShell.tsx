import type { CSSProperties } from 'react'
import { useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { SidebarInset, SidebarProvider } from '@/components/ui/sidebar'
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
  const [accountOpen, setAccountOpen] = useState(false)
  const displayName = [user.firstName, user.lastName].filter(Boolean).join(' ') || user.email

  return (
    <SidebarProvider
      style={{ '--sidebar-width': '16rem', '--sidebar-width-mobile': '18rem' } as CSSProperties}
    >
      <AccountSettings
        open={accountOpen}
        user={user}
        onProfile={onProfile}
        onClose={() => setAccountOpen(false)}
        onDeleted={onDeleted}
      />

      <AppSidebar
        displayName={displayName}
        onAccount={() => setAccountOpen(true)}
        onLogout={onLogout}
        signingOut={signingOut}
      />

      <SidebarInset>
        <Topbar />
        <main className="mx-auto grid w-full max-w-7xl flex-1 content-start gap-5 p-4 md:p-6 lg:p-8">
          {logoutError && (
            <Alert variant="destructive">
              <AlertDescription>{logoutError}</AlertDescription>
            </Alert>
          )}
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
