import { Icon } from '../../components/Icon'
import type { UserRole } from '../../types/dashboard'
import './LoginPage.css'

type LoginPageProps = {
  onLogin: (role: UserRole) => void
}

const accessOptions: Array<{
  role: UserRole
  title: string
  eyebrow: string
  description: string
  permissions: string[]
}> = [
  {
    role: 'viewer',
    title: 'Viewer',
    eyebrow: 'General access',
    description: 'Monitor the greenhouse without changing any live device or schedule state.',
    permissions: ['View live data and alerts', 'Review device timers', 'No control permissions'],
  },
  {
    role: 'operator',
    title: 'Advanced operator',
    eyebrow: 'Elevated access',
    description: 'Monitor the greenhouse and control approved devices, timers and responses.',
    permissions: ['All viewer permissions', 'Control timed outlets', 'Authorize schedule responses'],
  },
]

export function LoginPage({ onLogin }: LoginPageProps) {
  return (
    <main className="login-shell">
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-brand"><span><Icon name="leaf" size={22} /></span>Leafy.</div>
        <div className="login-copy">
          <span className="login-kicker"><Icon name="lock" size={14} />Protected greenhouse access</span>
          <h1 id="login-title">Choose a demo access level</h1>
          <p>This prototype uses role-based access so every user can see the same operational picture while controls stay protected.</p>
        </div>

        <div className="access-options">
          {accessOptions.map((option) => (
            <button
              className={`access-card ${option.role}`}
              type="button"
              onClick={() => onLogin(option.role)}
              key={option.role}
            >
              <span className="access-card-icon"><Icon name={option.role === 'operator' ? 'settings' : 'leaf'} size={20} /></span>
              <span className="access-card-copy">
                <small>{option.eyebrow}</small>
                <strong>{option.title}</strong>
                <em>{option.description}</em>
                <span className="permission-list">
                  {option.permissions.map((permission) => (
                    <span key={permission}><Icon name="check" size={13} />{permission}</span>
                  ))}
                </span>
              </span>
              <span className="access-continue">Continue <Icon name="arrow" size={15} /></span>
            </button>
          ))}
        </div>

        <p className="login-footnote">Demo access only · No password required</p>
      </section>

      <aside className="login-visual" aria-label="Leafy greenhouse operations">
        <div className="login-visual-mark"><Icon name="leaf" size={42} /></div>
        <div>
          <span>Northside Farm</span>
          <h2>One view for every growing decision.</h2>
          <p>Live conditions, device timing and risk-aware controls stay together—with access matched to each operator.</p>
        </div>
        <div className="login-status"><i />All monitoring systems online</div>
      </aside>
    </main>
  )
}
