import {
  CalendarDays,
  Car,
  Clock3,
  FileText,
  Globe2,
  Home,
  ShieldCheck,
  Trash2,
} from 'lucide-react'

const STATUS_CONFIG = {
  running: { color: '#2563eb', label: 'Running' },
  done: { color: '#16a34a', label: 'Done' },
  error: { color: '#dc2626', label: 'Error' },
}

const LOB_CONFIG = {
  'Personal Auto': { icon: Car, color: 'blue' },
  Homeowner: { icon: Home, color: 'green' },
  Cyber: { icon: ShieldCheck, color: 'purple' },
  'All LOBs': { icon: Globe2, color: 'orange' },
  General: { icon: FileText, color: 'blue' },
}

function elapsed(job) {
  const end = job.finished ?? Date.now() / 1000
  const secs = Math.max(0, Math.round(end - job.started))
  if (secs < 60) return `${secs}s`
  return `${Math.floor(secs / 60)}m ${secs % 60}s`
}

function startedTime(job) {
  return new Date(job.started * 1000).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function dayLabel(job) {
  const date = new Date(job.started * 1000)
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)

  if (date.toDateString() === today.toDateString()) return 'Today'
  if (date.toDateString() === yesterday.toDateString()) return 'Yesterday'

  return date.toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })
}

function inferLob(job) {
  const text = `${job.label || ''} ${job.result || ''}`.toLowerCase()
  if (text.includes('all lob')) return 'All LOBs'
  if (text.includes('homeowner') || text.includes('home ') || text.includes('ho_')) return 'Homeowner'
  if (text.includes('cyber')) return 'Cyber'
  if (text.includes('personal auto') || text.includes(' auto') || text.endsWith('auto')) return 'Personal Auto'
  return 'General'
}

function groupJobs(jobs) {
  return jobs.reduce((days, job) => {
    const day = dayLabel(job)
    const lob = inferLob(job)

    if (!days[day]) days[day] = {}
    if (!days[day][lob]) days[day][lob] = []
    days[day][lob].push(job)

    return days
  }, {})
}

export default function JobsPanel({ jobs, onSelect, onClearHistory }) {
  const grouped = groupJobs(jobs)
  const total = jobs.length
  const running = jobs.filter(job => job.status === 'running').length
  const completed = jobs.filter(job => job.status === 'done').length
  const failed = jobs.filter(job => job.status === 'error').length

  return (
    <div className="panel-stack jobs-panel-page">
      <div className="jobs-toolbar">
        <div className="page-heading">
          <h1>Jobs</h1>
          <p>Local dashboard history grouped by day and line of business.</p>
        </div>
        {total > 0 && (
          <button className="text-button danger" type="button" onClick={onClearHistory}>
            <Trash2 size={16} />
            Clear History
          </button>
        )}
      </div>

      <div className="jobs-summary-grid">
        <SummaryMetric label="Total jobs" value={total} />
        <SummaryMetric label="Running" value={running} />
        <SummaryMetric label="Completed" value={completed} />
        <SummaryMetric label="Failed" value={failed} />
      </div>

      {total === 0 ? (
        <div className="empty-history">
          <Clock3 size={58} strokeWidth={1.6} />
          <h2>No saved jobs yet</h2>
          <p>Run a policy flow and it will be saved here in this browser.</p>
        </div>
      ) : (
        Object.entries(grouped).map(([day, lobs]) => (
          <section className="job-day-section" key={day}>
            <div className="job-day-header">
              <CalendarDays size={20} />
              <h2>{day}</h2>
            </div>

            {Object.entries(lobs).map(([lob, lobJobs]) => (
              <div className="job-lob-section" key={`${day}-${lob}`}>
                <LobHeading lob={lob} count={lobJobs.length} />
                <div className="job-history-grid">
                  {lobJobs.map(job => (
                    <HistoryCard key={job.id} job={job} onSelect={onSelect} />
                  ))}
                </div>
              </div>
            ))}
          </section>
        ))
      )}
    </div>
  )
}

function SummaryMetric({ label, value }) {
  return (
    <div className="summary-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function LobHeading({ lob, count }) {
  const config = LOB_CONFIG[lob] || LOB_CONFIG.General
  const Icon = config.icon

  return (
    <div className="job-lob-heading">
      <span className={`customer-type-icon ${config.color}`}>
        <Icon size={22} />
      </span>
      <div>
        <h3>{lob}</h3>
        <p>{count} {count === 1 ? 'job' : 'jobs'}</p>
      </div>
    </div>
  )
}

function HistoryCard({ job, onSelect }) {
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.running
  const canOpen = job.status === 'done' || job.status === 'error'

  return (
    <article className="job-history-card">
      <div className="job-history-card-top">
        <span className="job-status" style={{ color: cfg.color }}>
          <i style={{ background: cfg.color }} />
          {cfg.label}
        </span>
        <span>{elapsed(job)}</span>
      </div>

      <h3>{job.label}</h3>
      <div className="job-history-meta">
        <span>Started {startedTime(job)}</span>
        <span>ID {job.id}</span>
      </div>

      {job.status === 'error' && job.error && (
        <div className="job-error">{job.error}</div>
      )}

      <div className="job-history-actions">
        {canOpen ? (
          <button className="text-button compact" type="button" onClick={() => onSelect(job)}>
            <FileText size={15} />
            View Report
          </button>
        ) : (
          <span className="job-running-note">Report available when the job finishes</span>
        )}
      </div>
    </article>
  )
}
