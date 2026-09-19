import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import leafyLogo from '../assets/Leafy_AI_logo.png'
import { Icon } from './Icon'
import { navItems } from './navigation'

type AppSidebarProps = {
  open: boolean
  onClose: () => void
  displayName: string
  onAccount: () => void
  onLogout: () => void
  signingOut: boolean
}

function initials(displayName: string) {
  const letters = displayName.split(' ').filter(Boolean).map((part) => part[0]).join('')
  return letters ? letters.slice(0, 2).toUpperCase() : '??'
}

export function AppSidebar({ open, onClose, displayName, onAccount, onLogout, signingOut }: AppSidebarProps) {
  const [profileOpen, setProfileOpen] = useState(false)

  return (
    <>
      <aside className={open ? 'sidebar open' : 'sidebar'}>
        <div className="brand">
          <img className="brand-logo" src={leafyLogo} alt="Leafy AI" />
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {navItems.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={onClose}
              className={({ isActive }) => (isActive ? 'active' : undefined)}
            >
              <Icon name={icon} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="profile account-menu">
          <button
            className="profile-trigger"
            type="button"
            onClick={() => setProfileOpen((value) => !value)}
            aria-expanded={profileOpen}
            disabled={signingOut}
          >
            <div className="avatar">{initials(displayName)}</div>
            <div>
              <strong>{signingOut ? 'Signing out…' : displayName}</strong>
              <span>Account settings</span>
            </div>
            <Icon name="more" size={18} />
          </button>
          {profileOpen && (
            <div className="account-options sidebar-account-options">
              <button type="button" onClick={() => { setProfileOpen(false); onAccount() }}>Account settings</button>
              <button type="button" onClick={() => { setProfileOpen(false); onLogout() }}>Sign out</button>
            </div>
          )}
        </div>
      </aside>

      {open && <button className="scrim" type="button" aria-label="Close navigation" onClick={onClose} />}
    </>
  )
}
