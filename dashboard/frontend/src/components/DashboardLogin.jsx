// import { useState } from 'react'
// import { LogIn } from 'lucide-react'
//
// export default function DashboardLogin({ onLogin }) {
//   const [username, setUsername] = useState('')
//
//   const submit = event => {
//     event.preventDefault()
//     const value = username.trim()
//     if (!value) return
//     onLogin(value)
//   }
//
//   return (
//     <main className="login-shell">
//       <section className="login-card">
//         <div className="brand-lockup login-brand">
//           <div className="brand-mark">IF</div>
//           <div>
//             <div className="brand-name">INFORCE</div>
//             <div className="brand-subtitle">Test Automation Dashboard</div>
//           </div>
//         </div>
//
//         <form onSubmit={submit} className="login-form">
//           <div>
//             <h1>Dashboard Login</h1>
//             <p>Enter your username to start a local dashboard session.</p>
//           </div>
//
//           <label htmlFor="dashboard-username">Username</label>
//           <input
//             id="dashboard-username"
//             className="field login-input"
//             value={username}
//             onChange={event => setUsername(event.target.value)}
//             autoComplete="username"
//             autoFocus
//             placeholder="e.g. gmilosavljevic"
//           />
//
//           <button className="action-button blue login-submit" type="submit" disabled={!username.trim()}>
//             <LogIn size={18} />
//             Sign In
//           </button>
//         </form>
//       </section>
//     </main>
//   )
// }
