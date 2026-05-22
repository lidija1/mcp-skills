import { useState, useEffect, useCallback, useRef } from 'react'
import Header from './components/Header'
import OverviewPanel from './components/OverviewPanel'
import PolicyPanel from './components/PolicyPanel'
import JobsPanel from './components/JobsPanel'
import ChatPanel from './components/ChatPanel'
import ReportModal from './components/ReportModal'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './components/LoginPage'
import RegisterPage from './components/RegisterPage'


import { api } from './utils/api'
import {
  AlertTriangle,
  CircleHelp,
  CalendarDays,
  CheckCircle2,
  Home,
  Menu,
  MessageCircle,
  Settings,
  UserCircle,
  Workflow,
  X,
} from 'lucide-react'
import { cleanDisplayText } from './utils/text'

const JOB_HISTORY_KEY = 'inforceDashboardJobHistory'
const MAX_STORED_JOBS = 100

function loadStoredJobs() {
  try {
    const raw = localStorage.getItem(JOB_HISTORY_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function normalizeJobUpdate(job, update) {
  if (!update) return job

  if (update.error === 'not found') {
    return {
      ...job,
      status: 'error',
      error: 'This running job was not found in the backend. Start it again to rerun the test.',
      finished: job.finished ?? Date.now() / 1000,
    }
  }

  return { ...job, ...update }
}

export default function AppWrapper() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  )
}

function App() {
  const [tab, setTab] = useState('overview')
  const [jobs, setJobs] = useState(() => loadStoredJobs())
  const [jobPopups, setJobPopups] = useState([])
  const [backendOk, setBackendOk] = useState(null)
  const [dashboardUser, setDashboardUser] = useState(() => {
  const token = localStorage.getItem('access_token')
  const user = localStorage.getItem('dashboardUser')

  return token && user ? user : ''
})
  const [showRegister, setShowRegister] = useState(false)
  const [selectedJob, setSelectedJob] = useState(null)
  const [showHelp, setShowHelp] = useState(false)
  const previousJobStatusRef = useRef(null)

  console.log("dashboardUser:", dashboardUser)

  useEffect(() => {
    api.health()
      .then(() => setBackendOk(true))
      .catch(() => setBackendOk(false))
  }, [])

  useEffect(() => {
    try {
      localStorage.setItem(JOB_HISTORY_KEY, JSON.stringify(jobs.slice(0, MAX_STORED_JOBS)))
    } catch {
      // Local history is convenience state. Ignore quota/private-mode failures.
    }
  }, [jobs])

  useEffect(() => {
    const running = jobs.filter(j => j.status === 'running')
    if (running.length === 0) return

    const timer = setInterval(async () => {
      const updates = await Promise.all(
        running.map(j => api.getJob(j.id).catch(() => ({ id: j.id, status: 'running' })))
      )
      setJobs(prev =>
        prev.map(j => {
          const upd = updates.find(u => u.id === j.id)
          return normalizeJobUpdate(j, upd)
        })
      )
    }, 2500)

    return () => clearInterval(timer)
  }, [jobs])

  useEffect(() => {
    if (previousJobStatusRef.current === null) {
      previousJobStatusRef.current = new Map(jobs.map(job => [job.id, job.status]))
      return
    }
    const token = localStorage.getItem('token')
    if (!token) {
  return <LoginPage onLogin={login} />
}

    const previousStatuses = previousJobStatusRef.current
    const completedJobs = jobs.filter(job => previousStatuses.get(job.id) === 'running' && job.status === 'done')
    if (completedJobs.length > 0) {
      setJobPopups(prev => {
        const existingIds = new Set(prev.map(item => item.id))
        const next = completedJobs
          .filter(job => !existingIds.has(job.id))
          .map(job => ({ id: job.id, job }))
        return [...next, ...prev].slice(0, 3)
      })
    }

    previousJobStatusRef.current = new Map(jobs.map(job => [job.id, job.status]))
  }, [jobs])

  useEffect(() => {
    if (jobPopups.length === 0) return
    const timers = jobPopups.map(popup =>
      setTimeout(() => {
        setJobPopups(prev => prev.filter(item => item.id !== popup.id))
      }, 15000)
    )
    return () => timers.forEach(clearTimeout)
  }, [jobPopups])

  useEffect(() => {
    if (!selectedJob) return
    const latestJob = jobs.find(job => job.id === selectedJob.id)
    if (latestJob && latestJob !== selectedJob) {
      setSelectedJob(latestJob)
    }
  }, [jobs, selectedJob])

  const submitJob = useCallback(async (apiFn, label) => {
    const data = await apiFn()
    if (!data.job_id) return
    const placeholder = {
      id: data.job_id,
      label,
      status: 'running',
      started: Date.now() / 1000,
      result: null,
      error: null,
      finished: null,
    }
    setJobs(prev => [placeholder, ...prev])
    return data.job_id
  }, [])

  const trackJob = useCallback((jobId, label) => {
    const placeholder = {
      id: jobId,
      label,
      status: 'running',
      started: Date.now() / 1000,
      result: null,
      error: null,
      finished: null,
    }
    setJobs(prev => {
      if (prev.some(j => j.id === jobId)) return prev
      return [placeholder, ...prev]
    })
  }, [])

  const dismissJobPopup = useCallback(jobId => {
    setJobPopups(prev => prev.filter(item => item.id !== jobId))
  }, [])

  const openJobReportFromPopup = useCallback(job => {
    const latest = jobs.find(item => item.id === job.id) || job
    setSelectedJob(latest)
    dismissJobPopup(job.id)
  }, [dismissJobPopup, jobs])

 const login = useCallback((username, token) => {
  localStorage.setItem('dashboardUser', username)
  localStorage.setItem('access_token', token)
  setDashboardUser(username)
}, [])

 const logout = useCallback(() => {
  localStorage.removeItem('dashboardUser')
  localStorage.removeItem('access_token')
  setDashboardUser('')
}, [])

if (!dashboardUser) {
  if (showRegister) {
    return (
      <RegisterPage
        onBackToLogin={() => setShowRegister(false)}
      />
    )
  }

  return (
    <LoginPage
      onLogin={login}
      onCreateAccount={() => setShowRegister(true)}
    />
  )
}

  return (
    <div className="app-shell">
      <Header backendOk={backendOk} user={dashboardUser} onLogout={logout} />

      <div className="workspace">
        <aside className="side-nav" aria-label="Primary navigation">
          <nav className="side-nav-main">
            <IconButton icon={Menu} label="Menu" />
            <NavItem icon={Home} label="Overview" active={tab === 'overview'} onClick={() => setTab('overview')} />
            <NavItem icon={CalendarDays} label="Jobs" active={tab === 'jobs'} onClick={() => setTab('jobs')} />
            <NavItem icon={Workflow} label="Policy Flow" active={tab === 'policy'} onClick={() => setTab('policy')} />
            <NavItem icon={Settings} label="Settings" />
          </nav>
          <nav className="side-nav-footer">
            <NavItem icon={CircleHelp} label="Help" onClick={() => setShowHelp(true)} />
            <NavItem icon={UserCircle} label="Account" />
          </nav>
        </aside>

        <main className="content-pane">
          {backendOk === false && (
            <div className="status-alert">
              Backend not reachable. Start it with <code>python dashboard/backend/main.py</code>
            </div>
          )}
          {tab === 'overview' && <OverviewPanel backendOk={backendOk} jobs={jobs} onOpenReport={setSelectedJob} />}
          {tab === 'jobs' && <JobsPanel jobs={jobs} onSelect={setSelectedJob} onClearHistory={() => setJobs([])} />}
          {tab === 'policy' && <PolicyPanel submitJob={submitJob} />}
        </main>

        <aside className="chat-sidebar" aria-label="Chat assistant">
          <div className="chat-sidebar-header">
            <MessageCircle size={17} />
            Chat Assistant
          </div>
          <ChatPanel onJobDispatched={trackJob} />
        </aside>

        <JobDonePopups
          popups={jobPopups}
          onOpenReport={openJobReportFromPopup}
          onDismiss={dismissJobPopup}
        />

        {selectedJob && <ReportModal job={selectedJob} onClose={() => setSelectedJob(null)} />}
        {showHelp && <HelpModal onClose={() => setShowHelp(false)} />}
      </div>
    </div>
  )
}

function isUwReferralJob(job) {
  const text = `${job?.result || ''} ${job?.error || ''}`.toLowerCase()
  return text.includes('uw referral') || text.includes('uw conditions triggered')
}

function JobDonePopups({ popups, onOpenReport, onDismiss }) {
  if (popups.length === 0) return null

  return (
    <div className="job-popup-stack" aria-live="polite" aria-label="Job notifications">
      {popups.map(({ id, job }) => (
        <section className={`job-done-popup ${isUwReferralJob(job) ? 'warning' : ''}`} key={id}>
          <div className="job-done-icon">
            {isUwReferralJob(job) ? <AlertTriangle size={20} /> : <CheckCircle2 size={20} />}
          </div>
          <div className="job-done-copy">
            <strong>{isUwReferralJob(job) ? 'UW referral triggered' : 'Job completed'}</strong>
            <span>{cleanDisplayText(job.label)}</span>
          </div>
          <button className="job-done-link" type="button" onClick={() => onOpenReport(job)}>
            Open report
          </button>
          <button
            className="job-done-dismiss"
            type="button"
            aria-label="Dismiss notification"
            onClick={() => onDismiss(id)}
          >
            <X size={16} />
          </button>
        </section>
      ))}
    </div>
  )
}

function IconButton({ icon: Icon, label }) {
  return (
    <button className="nav-icon-button" title={label} aria-label={label}>
      <Icon size={22} strokeWidth={2} />
    </button>
  )
}

function NavItem({ icon: Icon, label, active, onClick }) {
  return (
    <button className={`nav-item ${active ? 'active' : ''}`} onClick={onClick} type="button">
      <Icon size={22} strokeWidth={2} />
      <span>{label}</span>
    </button>
  )
}

function HelpModal({ onClose }) {
  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="help-backdrop" onClick={onClose} role="dialog" aria-modal="true" aria-label="Help">
      <div className="help-modal" onClick={e => e.stopPropagation()}>
        <div className="help-modal-header">
          <h2>How to use INFORCE</h2>
          <button className="help-modal-close" onClick={onClose} aria-label="Close help" type="button">
            <X size={18} />
          </button>
        </div>
        <div className="help-modal-body">
          <div className="help-section">
            <h3>Policy Flow</h3>
            <p>Generate a customer profile and run an end-to-end policy quote from a plain-English description. Choose a line of business, describe the customer, and click <strong>Run Policy Test</strong>.</p>
            <p>Use <strong>Build Customer Profile</strong> to generate structured JSON, then paste it into <strong>Run Policy Journey</strong> to replay it.</p>
          </div>
          <div className="help-section">
            <h3>Jobs</h3>
            <p>Every dispatched run appears in the Jobs tab. Jobs poll every 2.5 s while running. Click any completed job to open its report.</p>
          </div>
          <div className="help-section">
            <h3>Chat Assistant</h3>
            <p>Use the right-hand chat panel to describe a scenario in natural language. The assistant will dispatch a policy run and track the resulting job for you.</p>
          </div>
          <div className="help-section">
            <h3>Notifications</h3>
            <p>When a job finishes, a popup appears in the bottom-right corner. Click <strong>Open report</strong> to view results, or dismiss to close.</p>
          </div>
        </div>
      </div>
    </div>
  )
}
