import { Icon } from '../../components/Icon'

export function WelcomePanel() {
  return (
    <section className="welcome" id="overview">
      <div>
        <p className="eyebrow">Thursday, 30 July · 10:42 AM</p>
        <h1>Good morning, Alex</h1>
        <p>One active alert requires attention. All other systems are following today’s schedule.</p>
      </div>
      <button className="date-button" type="button">
        <Icon name="calendar" size={17} />
        Today
        <Icon name="chevron" size={14} />
      </button>
    </section>
  )
}
