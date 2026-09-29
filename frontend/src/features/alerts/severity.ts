import { InfoIcon, OctagonAlertIcon, TriangleAlertIcon } from 'lucide-react'
import type { AlertSeverity } from '../../api/alerts'

export const severityMeta: Record<AlertSeverity, { label: string, Icon: typeof InfoIcon }> = {
  critical: { label: 'Critical', Icon: OctagonAlertIcon },
  warning: { label: 'Warning', Icon: TriangleAlertIcon },
  info: { label: 'Info', Icon: InfoIcon },
}

export const alertTime = new Intl.DateTimeFormat(undefined, {
  day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
})
