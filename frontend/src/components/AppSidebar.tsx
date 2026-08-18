import { useState } from 'react'
import { Icon } from './Icon'

type AppSidebarProps = {
  open: boolean
  onClose: () => void
}

const primaryLinks = [
  { target: '#overview', icon: 'grid' as const, label: 'Overview' },
  { target: '#alerts', icon: 'alert' as const, label: 'Alerts', badge: '1' },
  { target: '#schedule', icon: 'schedule' as const, label: 'Schedule' },
  { target: '#ec-dose', icon: 'trend' as const, label: 'EC dosing' },
  { target: '#monitoring', icon: 'activity' as const, label: 'Monitoring' },
  { target: '#devices', icon: 'device' as const, label: 'Devices' },
]

export function AppSidebar({ open, onClose }: AppSidebarProps) {
  const [activeTarget, setActiveTarget] = useState('#overview')

  const navigateTo = (targetSelector: string) => {
    setActiveTarget(targetSelector)
    onClose()

    if (window.location.hash) {
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}`)
    }

    window.requestAnimationFrame(() => {
      const target = document.querySelector<HTMLElement>(targetSelector)
      const topbar = document.querySelector<HTMLElement>('.topbar')

      if (!target) return

      const navbarHeight = topbar?.getBoundingClientRect().height ?? 72
      const targetTop = target.getBoundingClientRect().top + window.scrollY
      const safeGap = 24

      window.scrollTo({
        top: Math.max(0, targetTop - navbarHeight - safeGap),
        behavior: 'smooth',
      })
    })
  }

  return (
    <>
      <aside className={open ? 'sidebar open' : 'sidebar'}>
        <div className="brand">
          <span className="brand-mark"><Icon name="leaf" size={21} /></span>
          <span>Leafy<span className="brand-dot">.</span></span>
        </div>

        <div className="site-switcher">
          <span className="site-icon"><Icon name="grid" size={18} /></span>
          <div>
            <small>Greenhouse</small>
            <strong>Northside Farm</strong>
          </div>
          <Icon name="chevron" size={15} />
        </div>

        <nav className="primary-nav" aria-label="Primary navigation">
          {primaryLinks.map(({ target, icon, label, badge }) => (
            <button
              className={activeTarget === target ? 'active' : undefined}
              type="button"
              onClick={() => navigateTo(target)}
              key={target}
            >
              <Icon name={icon} />
              {label}
              {badge && <span className="nav-alert-count">{badge}</span>}
            </button>
          ))}
        </nav>

        <div className="system-status">
          <span className="status-orbit"><i /></span>
          <div>
            <strong>All devices online</strong>
            <small>1 environmental alert</small>
          </div>
        </div>

        <nav className="secondary-nav" aria-label="Secondary navigation">
          <a href="#settings"><Icon name="settings" />Settings</a>
          <a href="#help"><Icon name="help" />Help centre</a>
        </nav>

        <div className="profile">
          <div className="avatar">AM</div>
          <div><strong>Alex Morgan</strong><span>Farm manager</span></div>
          <button type="button" aria-label="Profile options"><Icon name="more" size={18} /></button>
        </div>
      </aside>

      {open && <button className="scrim" type="button" aria-label="Close navigation" onClick={onClose} />}
    </>
  )
}
