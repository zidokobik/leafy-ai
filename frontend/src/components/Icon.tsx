import type { ReactNode } from 'react'

export type IconName =
  | 'activity'
  | 'alert'
  | 'arrow'
  | 'bell'
  | 'calendar'
  | 'camera'
  | 'check'
  | 'chevron'
  | 'clock'
  | 'device'
  | 'droplet'
  | 'grid'
  | 'help'
  | 'leaf'
  | 'lock'
  | 'menu'
  | 'minus'
  | 'more'
  | 'plus'
  | 'schedule'
  | 'settings'
  | 'sun'
  | 'temperature'
  | 'trend'
  | 'x'

const paths: Record<IconName, ReactNode> = {
  activity: <path d="M3 12h4l2-7 4 14 2-7h6" />,
  alert: <path d="M12 9v4m0 4h.01M10.3 3.6 2.5 17A2 2 0 0 0 4.2 20h15.6a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z" />,
  arrow: <path d="M5 12h14m-5-5 5 5-5 5" />,
  bell: <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />,
  calendar: <path d="M6 2v4m12-4v4M3 9h18M5 4h14a2 2 0 0 1 2 2v15H3V6a2 2 0 0 1 2-2Z" />,
  camera: <path d="M14.5 4 16 7h3a2 2 0 0 1 2 2v9H3V9a2 2 0 0 1 2-2h3l1.5-3Zm1.5 8a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z" />,
  check: <path d="m5 12 4 4L19 6" />,
  chevron: <path d="m9 18 6-6-6-6" />,
  clock: <path d="M12 7v5l3 2m7-2A10 10 0 1 1 2 12a10 10 0 0 1 20 0Z" />,
  device: <path d="M7 2h10v20H7zM10 18h4M10 6h4" />,
  droplet: <path d="M12 2S5 10 5 15a7 7 0 0 0 14 0c0-5-7-13-7-13Z" />,
  grid: <path d="M4 4h6v6H4zm10 0h6v6h-6zM4 14h6v6H4zm10 0h6v6h-6z" />,
  help: <path d="M9.1 9a3 3 0 1 1 4.6 2.5c-1.3.8-1.7 1.5-1.7 2.5m0 4h.01M22 12A10 10 0 1 1 2 12a10 10 0 0 1 20 0Z" />,
  leaf: <path d="M20.5 3.5C12 3 5 6 4 13c-.7 4.5 3.7 7.8 7.6 5.6C16 16 17 10 20.5 3.5ZM4 21c2-6 6-9 12-12" />,
  lock: <path d="M6 10h12v11H6zM8 10V7a4 4 0 0 1 8 0v3m-4 4v3" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  minus: <path d="M5 12h14" />,
  more: <path d="M5 12h.01M12 12h.01M19 12h.01" />,
  plus: <path d="M12 5v14M5 12h14" />,
  schedule: <path d="M4 5h16v16H4zM8 3v4m8-4v4M4 10h16M8 14h3m-3 3h7" />,
  settings: <path d="M12 15.5a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm8-3.5 2-1-2-3-2 .3a8 8 0 0 0-1.4-.8L16 5h-4l-.7 2.5a8 8 0 0 0-1.4.8L8 8 6 11l2 1a8 8 0 0 0 0 1.7l-2 1 2 3 2-.3a8 8 0 0 0 1.4.8L12 21h4l.7-2.5a8 8 0 0 0 1.4-.8l2 .3 2-3-2-1a8 8 0 0 0 0-1.7Z" />,
  sun: <path d="M12 3V1m0 22v-2M3 12H1m22 0h-2M4.2 4.2 2.8 2.8m18.4 18.4-1.4-1.4m0-15.6 1.4-1.4M2.8 21.2l1.4-1.4M17 12a5 5 0 1 1-10 0 5 5 0 0 1 10 0Z" />,
  temperature: <path d="M14 14.8V5a4 4 0 0 0-8 0v9.8a6 6 0 1 0 8 0ZM10 6v10" />,
  trend: <path d="m3 17 6-6 4 4 8-9m-5 0h5v5" />,
  x: <path d="m6 6 12 12M18 6 6 18" />,
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
