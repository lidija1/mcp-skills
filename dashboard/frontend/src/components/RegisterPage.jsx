import { useState } from 'react'
import { api } from '../utils/api'
import '../styles/auth.css'

export default function RegisterPage({ onBackToLogin }) {
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async e => {
    e.preventDefault()

    setError('')
    setLoading(true)

    try {
      await api.register(
        firstName,
        lastName,
        username,
        password
      )

      alert('Account created successfully')

      onBackToLogin()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>Create Account</h1>

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="First name"
            value={firstName}
            onChange={e => setFirstName(e.target.value)}
            required
          />

          <input
            type="text"
            placeholder="Last name"
            value={lastName}
            onChange={e => setLastName(e.target.value)}
            required
          />

          <input
            type="text"
            placeholder="Username"
            value={username}
            onChange={e => setUsername(e.target.value)}
            required
          />

          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
          />

          {error && (
            <div className="auth-error">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}>
            {loading ? 'Creating...' : 'Create Account'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account?
          <button
            type="button"
            className="link-button"
            onClick={onBackToLogin}
          >
            Login
          </button>
        </div>
      </div>
    </div>
  )
}