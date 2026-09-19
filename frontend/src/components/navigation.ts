import type { IconName } from './Icon'

export type NavItem = {
  to: string
  icon: IconName
  label: string
}

export const navItems: NavItem[] = [
  { to: '/', icon: 'grid', label: 'Overview' },
  { to: '/agents', icon: 'chat', label: 'Agents' },
  { to: '/schedules', icon: 'schedule', label: 'Schedules' },
  { to: '/devices', icon: 'device', label: 'Devices' },
]

export function pageTitle(pathname: string) {
  const match = navItems.find((item) => (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)))
  return match?.label ?? 'Leafy'
}
