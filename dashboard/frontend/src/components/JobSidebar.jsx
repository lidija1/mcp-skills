import { Clock3, MoreVertical, RefreshCcw } from 'lucide-react'
import { cleanDisplayText } from '../utils/text'

const STATUS_CONFIG = {
  running: { color: '#2563eb', label: 'Running' },
  done: { color: '#16a34a', label: 'Done' },
  error: { color: '#dc2626', label: 'Error' },
}

function elapsed(job) {
  const end = job.finished ?? Date.now() / 1000
  const secs = Math.max(0, Math.round(end - job.started))
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

export default function JobSidebar({ jobs, onSelect, selectedId }) {
  const runningCount = jobs.filter(j => j.status === 'running').length

  return (
    <aside className="job-panel">
      <div className="job-panel-header">
        <div>
          <h2>Job History</h2>
          {runningCount > 0 && <span>{runningCount} running</span>}
        </div>
        <div className="job-actions">
          <button title="Refresh" aria-label="Refresh jobs" type="button">
            <RefreshCcw size={20} />
          </button>
          <button title="More" aria-label="More job actions" type="button">
            <MoreVertical size={20} />
          </button>
        </div>
      </div>

      <div className="job-list">
        {jobs.length === 0 ? (
          <div className="empty-jobs">
            <Clock3 size={58} strokeWidth={1.6} />
            <h3>No jobs yet</h3>
            <p>Your job history will appear here once you run a policy test.</p>
          </div>
        ) : (
          jobs.map(job => (
            <JobCard key={job.id} job={job} onSelect={onSelect} isSelected={job.id === selectedId} />
          ))
        )}
      </div>
    </aside>
  )
}

function JobCard({ job, onSelect, isSelected }) {
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.running
  const clickable = job.status === 'done' || job.status === 'error'

  return (
    <button
      onClick={() => clickable && onSelect(job)}
      className={`job-card ${isSelected ? 'selected' : ''}`}
      disabled={!clickable}
      type="button"
    >
      <div className="job-card-top">
        <span className="job-status" style={{ color: cfg.color }}>
          <i style={{ background: cfg.color }} />
          {cfg.label}
        </span>
        <span>{elapsed(job)}</span>
      </div>
      <div className="job-label">{cleanDisplayText(job.label)}</div>
      {job.status === 'error' && job.error && (
        <div className="job-error">{job.error}</div>
      )}
      {clickable && <div className="job-hint">View report</div>}
    </button>
  )
}
