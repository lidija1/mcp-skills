import {Bell, LogOut} from 'lucide-react'

export default function Header({backendOk, user, onLogout}) {
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
