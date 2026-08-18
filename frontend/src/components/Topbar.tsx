import { Icon } from './Icon'
import type { UserRole } from '../types/dashboard'

type TopbarProps = {
  role: UserRole
  onLogout: () => void
  onOpenMenu: () => void
}

export function Topbar({ role, onLogout, onOpenMenu }: TopbarProps) {
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
        <button className="top-profile" type="button" onClick={onLogout} title="Sign out and switch access level">
          <span>{role === 'operator' ? 'AO' : 'VW'}</span>
          <strong>{role === 'operator' ? 'Advanced operator' : 'Viewer'}</strong>
          <Icon name="x" size={14} />
        </button>
      </div>
    </header>
  )
}
