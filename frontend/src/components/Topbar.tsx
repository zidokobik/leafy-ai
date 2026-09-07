import { Icon } from './Icon'
import type { UserRole } from '../types/dashboard'

type TopbarProps = {
  role: UserRole
  onLogout: () => void
  signingOut: boolean
  onOpenMenu: () => void
  displayName: string
  onAccount: () => void
}

export function Topbar({ role, onLogout, onOpenMenu, signingOut, displayName, onAccount }: TopbarProps) {
  const [expanded, setExpanded] = useState(false)
  const container = useRef<HTMLDivElement>(null)
  const trigger = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!expanded) return
    const dismiss = (event: PointerEvent) => {
      if (!container.current?.contains(event.target as Node)) setExpanded(false)
    }
    document.addEventListener('pointerdown', dismiss)
    return () => document.removeEventListener('pointerdown', dismiss)
  }, [expanded])
  return (
    <header className="topbar">
      <button className="mobile-menu" type="button" onClick={onOpenMenu} aria-label="Open navigation">
        <Icon name="menu" />
      </button>
      <div className="breadcrumb">
        <span>Northside Farm</span>
        <Icon name="chevron" size={13} />
        <strong>Overview</strong>
      </div>
      <div className="top-actions">
        <span className="sync-status"><i />Live data</span>
        <button className="icon-button notification" type="button" aria-label="Notifications">
          <Icon name="bell" size={19} />
          <span />
        </button>
        <div className="account-menu" ref={container} onKeyDown={(event) => {
          if (event.key === 'Escape') { setExpanded(false); trigger.current?.focus() }
        }} onBlur={(event) => {
          if (!event.currentTarget.contains(event.relatedTarget)) setExpanded(false)
        }}>
        <button ref={trigger} className="top-profile" type="button" onClick={() => setExpanded(!expanded)} disabled={signingOut}
          aria-label={`Account: ${displayName}`} aria-expanded={expanded} aria-controls="account-options" title={displayName}>
          <span>{role === 'admin' ? 'AD' : role === 'operator' ? 'AO' : 'VW'}</span>
          <strong>{signingOut ? 'Signing out…' : displayName}</strong>
          <span className="account-chevron"><Icon name="chevron" size={14} /></span>
        </button>
        {expanded && <div id="account-options" className="account-options">
          <button type="button" onClick={() => { setExpanded(false); onAccount() }}>Account settings</button>
          <button type="button" onClick={() => { setExpanded(false); onLogout() }}>Sign out</button>
        </div>}
        </div>
      </div>
    </header>
  )
}
import { useEffect, useRef, useState } from 'react'
