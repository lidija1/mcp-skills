import { useState } from 'react'
import { api } from '../utils/api'
import '../styles/auth.css'

export default function LoginPage({
  onLogin,
  onCreateAccount,
}) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async e => {
    e.preventDefault()

    setError('')
    setLoading(true)

    try {
      const data = await api.login(username, password)

      if (data.access_token) {
        localStorage.setItem('access_token', data.access_token)
      }
      onLogin(data.user)

    } catch (err) {
      setError(err.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <div className="auth-mark">IF</div>
          <div>
            <h1>INFORCE Dashboard</h1>
            <p className="auth-subtitle">Sign in to run and review dashboard executions.</p>
          </div>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="auth-field">
            <label htmlFor="dashboard-username">Username</label>
            <input
              id="dashboard-username"
              type="text"
              placeholder="e.g. ldubovac"
              value={username}
              onChange={e => setUsername(e.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="auth-field">
            <label htmlFor="dashboard-password">Password</label>
            <input
              id="dashboard-password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}>
            {loading ? 'Signing in...' : 'Login'}
          </button>
        </form>

        <div className="auth-footer">
          Don't have an account?

          <button
            type="button"
            className="link-button"
            onClick={onCreateAccount}
          >
            Create Account
          </button>
        </div>
      </div>
    </div>
  )
}
