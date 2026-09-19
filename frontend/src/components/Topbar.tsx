import { useLocation } from 'react-router-dom'
import { Icon } from './Icon'
import { pageTitle } from './navigation'

type TopbarProps = { onOpenMenu: () => void }

export function Topbar({ onOpenMenu }: TopbarProps) {
  const { pathname } = useLocation()

  return (
    <header className="topbar">
      <button className="mobile-menu" type="button" onClick={onOpenMenu} aria-label="Open navigation">
        <Icon name="menu" />
      </button>
      <h2 className="topbar-title">{pageTitle(pathname)}</h2>
    </header>
  )
}
