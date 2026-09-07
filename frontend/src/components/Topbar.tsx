import { Icon } from './Icon'

type TopbarProps = { onOpenMenu: () => void }

export function Topbar({ onOpenMenu }: TopbarProps) {
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
      </div>
    </header>
  )
}
