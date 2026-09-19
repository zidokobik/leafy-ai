import type { ReactNode } from 'react'

export type IconName =
  | 'chat'
  | 'clock'
  | 'device'
  | 'grid'
  | 'menu'
  | 'more'
  | 'schedule'

const paths: Record<IconName, ReactNode> = {
  chat: <path d="M21 14a2 2 0 0 1-2 2H8l-5 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z" />,
  clock: <path d="M12 7v5l3 2m7-2A10 10 0 1 1 2 12a10 10 0 0 1 20 0Z" />,
  device: <path d="M7 2h10v20H7zM10 18h4M10 6h4" />,
  grid: <path d="M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  more: <path d="M5 12h.01M12 12h.01M19 12h.01" />,
  schedule: <path d="M4 5h16v16H4zM8 3v4m8-4v4M4 10h16M8 14h3m-3 3h7" />,
}

type IconProps = {
  name: IconName
  size?: number
}

export function Icon({ name, size = 20 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  )
}
