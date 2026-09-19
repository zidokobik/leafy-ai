import { ClockIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'

type ComingSoonProps = {
  title: string
  description: string
  status?: string
}

export function ComingSoon({ title, description, status = 'Coming soon' }: ComingSoonProps) {
  return (
    <Empty className="min-h-[52vh] border bg-card">
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <ClockIcon />
        </EmptyMedia>
        <Badge variant="secondary">{status}</Badge>
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{description}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  )
}
