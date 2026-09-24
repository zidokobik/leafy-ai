import { BotIcon, CalendarDaysIcon, LayoutDashboardIcon, SproutIcon, Logs } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

export type NavItem = {
  to: string
  icon: LucideIcon
  label: string
}

export const navItems: NavItem[] = [
  { to: '/', icon: LayoutDashboardIcon, label: 'Overview' },
  { to: '/agents', icon: BotIcon, label: 'Agents' },
  { to: '/schedules', icon: CalendarDaysIcon, label: 'Schedules' },
  { to: '/devices', icon: SproutIcon, label: 'Devices' },
  {to : '/logs', icon:Logs, label: 'Logs' },
]

export function pageTitle(pathname: string) {
  const match = navItems.find((item) => (item.to === '/' ? pathname === '/' : pathname.startsWith(item.to)))
  return match?.label ?? 'Leafy'
}
