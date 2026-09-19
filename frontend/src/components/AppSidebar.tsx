import { ChevronUpIcon, LogOutIcon, SettingsIcon } from 'lucide-react'
import { NavLink } from 'react-router-dom'
import { useLocation } from 'react-router-dom'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  useSidebar,
} from '@/components/ui/sidebar'
import leafyLogo from '../assets/Leafy_AI_logo.png'
import { navItems } from './navigation'

type AppSidebarProps = {
  displayName: string
  onAccount: () => void
  onLogout: () => void
  signingOut: boolean
}

function initials(displayName: string) {
  const letters = displayName.split(' ').filter(Boolean).map((part) => part[0]).join('')
  return letters ? letters.slice(0, 2).toUpperCase() : '??'
}

export function AppSidebar({ displayName, onAccount, onLogout, signingOut }: AppSidebarProps) {
  const { pathname } = useLocation()
  const { setOpenMobile } = useSidebar()

  return (
    <Sidebar collapsible="offcanvas">
      <SidebarHeader className="p-4">
        <div className="flex h-10 items-center">
          <img className="h-8 w-auto" src={leafyLogo} alt="Leafy AI" />
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map(({ to, icon: Icon, label }) => {
                const isActive = to === '/' ? pathname === '/' : pathname.startsWith(to)

                return (
                  <SidebarMenuItem key={to}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      tooltip={label}
                      size="lg"
                      className={label === 'Devices' ? 'text-base [&_svg]:size-5' : 'text-base'}
                    >
                      <NavLink to={to} end={to === '/'} onClick={() => setOpenMobile(false)}>
                        <Icon />
                        <span>{label}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                )
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <SidebarMenuButton size="lg" disabled={signingOut}>
                  <Avatar>
                    <AvatarFallback>{initials(displayName)}</AvatarFallback>
                  </Avatar>
                  <span className="grid flex-1 text-left leading-tight">
                    <span className="truncate font-medium">{signingOut ? 'Signing out...' : displayName}</span>
                    <span className="truncate text-xs text-muted-foreground">Account settings</span>
                  </span>
                  <ChevronUpIcon />
                </SidebarMenuButton>
              </DropdownMenuTrigger>
              <DropdownMenuContent side="top" align="end" className="w-[--radix-popper-anchor-width]">
                <DropdownMenuLabel>Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuGroup>
                  <DropdownMenuItem onClick={onAccount}>
                    <SettingsIcon />
                    Account settings
                  </DropdownMenuItem>
                  <DropdownMenuItem onClick={onLogout}>
                    <LogOutIcon />
                    Sign out
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </DropdownMenuContent>
            </DropdownMenu>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}
