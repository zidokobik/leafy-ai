import { Icon } from './Icon'

type ComingSoonProps = {
  title: string
  description: string
  status?: string
}

export function ComingSoon({ title, description, status = 'Coming soon' }: ComingSoonProps) {
  return (
    <section className="coming-soon">
      <span className="coming-soon-badge"><Icon name="clock" size={15} />{status}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </section>
  )
}
