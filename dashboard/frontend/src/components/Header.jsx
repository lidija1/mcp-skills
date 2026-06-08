import {Bell, LogOut} from 'lucide-react'
import {useEffect, useState} from 'react'

const ENV_COLORS = {
  prod:       { bg: '#fee2e2', text: '#991b1b', dot: '#dc2626' },
  production: { bg: '#fee2e2', text: '#991b1b', dot: '#dc2626' },
  test:       { bg: '#fef9c3', text: '#854d0e', dot: '#ca8a04' },
  staging:    { bg: '#fef9c3', text: '#854d0e', dot: '#ca8a04' },
  sandbox:    { bg: '#dcfce7', text: '#166534', dot: '#16a34a' },
  dev:        { bg: '#dbeafe', text: '#1e40af', dot: '#2563eb' },
}

function envStyle(env) {
  return ENV_COLORS[env?.toLowerCase()] ?? { bg: '#f1f5f9', text: '#475569', dot: '#94a3b8' }
}

export default function Header({backendOk, user, onLogout}) {
    const [env, setEnv] = useState(null)
    useEffect(() => {
        fetch('/api/config').then(r => r.json()).then(d => setEnv(d.environment)).catch(() => {})
    }, [])

    const displayName = typeof user === 'string' ? user : user?.display_name || user?.username || 'User'
    const username = typeof user === 'string' ? user : user?.username
    const role = typeof user === 'string' ? '' : user?.role
    const initials = displayName
        .split(/[.\s_-]+/)
        .filter(Boolean)
        .slice(0, 2)
        .map(part => part[0]?.toUpperCase())
        .join('') || 'U'

    return (<header className="top-bar">
        <div className="brand-lockup">
            <div className="brand-mark">IF</div>
            <div>
                <div className="brand-name">INFORCE</div>
                <div className="brand-subtitle">Test Automation Dashboard</div>
            </div>
        </div>

        <div className="top-actions">
            {env && (() => {
                const s = envStyle(env)
                return (
                    <div className="env-chip" style={{background: s.bg, color: s.text}} title={`Environment: ${env}`}>
                        <span style={{background: s.dot}}/>
                        {env.toUpperCase()}
                    </div>
                )
            })()}
            <div className={`backend-chip ${backendOk === false ? 'offline' : ''}`}>
                <span/>
                {backendOk === null ? 'Connecting' : backendOk ? 'Backend online' : 'Backend offline'}
            </div>
            <button className="icon-action" title="Notifications" aria-label="Notifications">
                <Bell size={21}/>
            </button>
            <button className="profile-button" title="Sign out" aria-label={`Signed in as ${displayName}. Sign out`}>
                <span className="profile-initials">{initials}</span>
                <span className="profile-copy">
                <strong>{displayName}</strong>
                    {role === 'admin' ? <small>Admin{username ? ` - ${username}` : ''}</small> : username ?
                        <small>{username}</small> : null}
                    </span>
                <LogOut size={18} onClick={() => {
                    const confirmed = window.confirm('Do you want to log out?')

                    if (confirmed) {
                        onLogout()
                    }
                }}/>
            </button>
        </div>
    </header>)
}
