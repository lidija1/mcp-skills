import { useState, useEffect, useCallback } from 'react'
import Header from './components/Header'
import OverviewPanel from './components/OverviewPanel'
import PolicyPanel from './components/PolicyPanel'
import JobsPanel from './components/JobsPanel'
import ChatPanel from './components/ChatPanel'
import ReportModal from './components/ReportModal'
import DashboardLogin from './components/DashboardLogin'
import { api } from './utils/api'
import {
  CircleHelp,
  CalendarDays,
  Home,
  Menu,
  MessageCircle,
  Settings,
  UserCircle,
  Workflow,
} from 'lucide-react'

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

  return update.status !== 'running' ? { ...job, ...update } : job
}

export default function App() {
  const [tab, setTab] = useState('overview')
  const [jobs, setJobs] = useState(() => loadStoredJobs())
  const [backendOk, setBackendOk] = useState(null)
  const [dashboardUser, setDashboardUser] = useState(() => localStorage.getItem('dashboardUser') || '')
  const [selectedJob, setSelectedJob] = useState(null)

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

  const login = useCallback(username => {
    localStorage.setItem('dashboardUser', username)
    setDashboardUser(username)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('dashboardUser')
    setDashboardUser('')
  }, [])

  if (!dashboardUser) {
    return <DashboardLogin onLogin={login} />
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
            <NavItem icon={CircleHelp} label="Help" />
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

        {selectedJob && <ReportModal job={selectedJob} onClose={() => setSelectedJob(null)} />}
      </div>
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
