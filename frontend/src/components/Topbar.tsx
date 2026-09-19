import { useLocation } from 'react-router-dom'
import { Separator } from '@/components/ui/separator'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { pageTitle } from './navigation'

export function Topbar() {
  const { pathname } = useLocation()

  return (
    <header className="sticky top-0 z-20 flex h-14 shrink-0 items-center gap-3 border-b bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:px-6">
      <SidebarTrigger />
      <Separator orientation="vertical" className="h-5" />
      <h2 className="text-base font-medium">{pageTitle(pathname)}</h2>
    </header>
  )
}
