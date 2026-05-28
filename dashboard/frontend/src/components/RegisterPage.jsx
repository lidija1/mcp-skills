import {useState} from 'react'
import {api} from '../utils/api'
import '../styles/auth.css'

export default function RegisterPage({onBackToLogin}) {
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

        const nameRegex = /^[A-Za-zÀ-ž\s-]{2,}$/

        if (!nameRegex.test(firstName.trim())) {
            setError(
                'First name must contain at least 2 letters and cannot contain numbers or special characters.'
            )
            setLoading(false)
            return
        }

        if (!nameRegex.test(lastName.trim())) {
            setError(
                'Last name must contain at least 2 letters and cannot contain numbers or special characters.'
            )
            setLoading(false)
            return
        }

        const passwordRegex = /^(?=.*[A-Za-z])(?=.*[\d\W]).{8,}$/

        if (username.trim().length < 3) {
            setError('Username must contain at least 3 characters.')
            setLoading(false)
            return
        }

        if (!passwordRegex.test(password)) {
            setError(
                'Password must be at least 8 characters long and contain at least one letter plus one number or special character.'
            )
            setLoading(false)
            return
        }

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
                <div className="auth-brand">
                    <div className="auth-mark">IF</div>
                    <div>
                        <h1>Create Account</h1>
                        <p className="auth-subtitle">Create a dashboard user for execution history ownership.</p>
                    </div>
                </div>

                <form onSubmit={handleSubmit}>
                    <div className="auth-field">
                        <label htmlFor="register-first-name">First name</label>
                        <input
                            id="register-first-name"
                            type="text"
                            placeholder="First name"
                            value={firstName}
                            onChange={e => setFirstName(e.target.value)}
                            autoComplete="given-name"
                            required
                        />
                    </div>

                    <div className="auth-field">
                        <label htmlFor="register-last-name">Last name</label>
                        <input
                            id="register-last-name"
                            type="text"
                            placeholder="Last name"
                            value={lastName}
                            onChange={e => setLastName(e.target.value)}
                            autoComplete="family-name"
                            required
                        />
                    </div>

                    <div className="auth-field">
                        <label htmlFor="register-username">Username</label>
                        <input
                            id="register-username"
                            type="text"
                            placeholder="Username"
                            value={username}
                            onChange={e => setUsername(e.target.value)}
                            autoComplete="username"
                            required
                        />
                    </div>

                    <div className="auth-field">
                        <label htmlFor="register-password">Password</label>
                        <input
                            id="register-password"
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            autoComplete="new-password"
                            required
                        />
                    </div>

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
