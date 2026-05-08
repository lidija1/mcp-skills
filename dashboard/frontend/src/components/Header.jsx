import { Bell, LogOut } from 'lucide-react'

export default function Header({ backendOk, user, onLogout }) {
  const initials = user
    .split(/[.\s_-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part[0]?.toUpperCase())
    .join('') || 'U'

  return (
    <header className="top-bar">
      <div className="brand-lockup">
        <div className="brand-mark">IF</div>
        <div>
          <div className="brand-name">INFORCE</div>
          <div className="brand-subtitle">Test Automation Dashboard</div>
        </div>
      </div>

      <div className="top-actions">
        <div className={`backend-chip ${backendOk === false ? 'offline' : ''}`}>
          <span />
          {backendOk === null ? 'Connecting' : backendOk ? 'Backend online' : 'Backend offline'}
        </div>
        <button className="icon-action" title="Notifications" aria-label="Notifications">
          <Bell size={21} />
        </button>
        <button className="profile-button" title="Sign out" aria-label={`Signed in as ${user}. Sign out`} onClick={onLogout}>
          <span>{initials}</span>
          <LogOut size={18} />
        </button>
      </div>
    </header>
  )
}
