import {
  Activity,
  CalendarDays,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'

export default function OverviewPanel({ backendOk, jobs }) {
  const completed = jobs.filter(job => job.status === 'done').length
  const running = jobs.filter(job => job.status === 'running').length
  const failed = jobs.filter(job => job.status === 'error').length

  return (
    <div className="overview-panel">
      <section className="overview-hero">
        <div className="overview-logo-card" aria-label="INFORCE logo">
          <div className="inforce-logo-word">INFORCE</div>
          <div className="inforce-logo-tagline">YOUR FIERCEST ALLY</div>
        </div>

        <div className="overview-hero-copy">
          <span className="overview-eyebrow">
            <Sparkles size={16} />
            Test Automation Dashboard
          </span>
          <h1>Insurance workflow automation in one focused console.</h1>
          <p>
            INFORCE brings policy creation, local job history, and report viewing into a
            single dashboard for repeatable demos and faster QA feedback.
          </p>
        </div>
      </section>

      <section className="overview-metrics" aria-label="Application status">
        <MetricCard
          icon={Activity}
          label="Backend"
          value={backendOk === null ? 'Connecting' : backendOk ? 'Online' : 'Offline'}
          tone={backendOk === false ? 'red' : 'green'}
        />
        <MetricCard icon={CalendarDays} label="Saved jobs" value={jobs.length} tone="blue" />
        <MetricCard icon={CheckCircle2} label="Completed" value={completed} tone="green" />
        <MetricCard icon={Activity} label="Running / Failed" value={`${running} / ${failed}`} tone="purple" />
      </section>
    </div>
  )
}

function MetricCard({ icon: Icon, label, value, tone }) {
  return (
    <div className="overview-metric-card">
      <span className={`customer-type-icon ${tone}`}>
        <Icon size={22} />
      </span>
      <div>
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
    </div>
  )
}
