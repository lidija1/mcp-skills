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
  const dateText = date.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  })

  if (date.toDateString() === today.toDateString()) return `Today - ${dateText}`
  if (date.toDateString() === yesterday.toDateString()) return `Yesterday - ${dateText}`

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
          <h2>No saved jobs yet</h2>
          <p>Run a policy flow and it will be saved here in this browser.</p>
        </div>
      ) : (
        <div className="jobs-table-card">
          <div className="jobs-table-header" role="row">
            <span>Group / Job</span>
            <span>Status</span>
            <span>Started</span>
            <span>Duration</span>
            <span>ID</span>
            <span />
          </div>

          <div className="jobs-table-body">
            {Object.entries(grouped).map(([day, lobs]) => {
              const dayCount = Object.values(lobs).reduce((sum, lobJobs) => sum + lobJobs.length, 0)

              return (
                <section className="jobs-day-group" key={day}>
                  <div className="jobs-group-row jobs-day-row">
                    <div className="jobs-group-title">
                      <strong>{day}</strong>
                      <span>{dayCount} {dayCount === 1 ? 'job' : 'jobs'}</span>
                    </div>
                    <span className="jobs-collapse-marker">v</span>
                  </div>

                  {Object.entries(lobs).map(([lob, lobJobs]) => (
                    <div className="jobs-lob-group" key={`${day}-${lob}`}>
                      <div className="jobs-group-row jobs-lob-row">
                        <div className="jobs-group-title">
                          <strong>{lob}</strong>
                          <span>{lobJobs.length} {lobJobs.length === 1 ? 'job' : 'jobs'}</span>
                        </div>
                      </div>

                      {lobJobs.map(job => (
                        <HistoryRow key={job.id} job={job} onSelect={onSelect} />
                      ))}
                    </div>
                  ))}
                </section>
              )
            })}
          </div>
        </div>
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

function HistoryRow({ job, onSelect }) {
  const cfg = STATUS_CONFIG[job.status] || STATUS_CONFIG.running
  const canOpen = job.status === 'done' || job.status === 'error'

  return (
    <article className={`jobs-table-row ${job.status === 'error' ? 'has-error' : ''}`}>
      <div className="jobs-job-title">{job.label}</div>
      <div>
        <span className="job-status" style={{ color: cfg.color }}>
          <i style={{ background: cfg.color }} />
          {cfg.label}
        </span>
      </div>
      <div className="jobs-cell-muted">{startedTime(job)}</div>
      <div className="jobs-cell-muted">{elapsed(job)}</div>
      <div className="jobs-cell-id" title={job.id}>{job.id}</div>
      <div className="jobs-report-cell">
        {canOpen ? (
          <button className="jobs-report-link" type="button" onClick={() => onSelect(job)}>
            View Report
          </button>
        ) : (
          <span className="job-running-note">Pending</span>
        )}
      </div>
      {job.status === 'error' && job.error && (
        <div className="job-error">{job.error}</div>
      )}
    </article>
  )
}
