import {
  Activity,
  CalendarDays,
  CheckCircle2,
  Sparkles,
  Workflow,
} from 'lucide-react'

const FEATURES = [
  {
    icon: Workflow,
    color: 'blue',
    title: 'Policy Flow Generator',
    copy: 'Creates realistic customer profiles and runs full policy workflows for Auto, Cyber, and Homeowner.',
    action: 'Open Policy Flow',
    target: 'policy',
  },
  {
    icon: CalendarDays,
    color: 'green',
    title: 'Job History',
    copy: 'Shows saved dashboard runs with status, timing, and generated reports for completed policy tests.',
    action: 'View Jobs',
    target: 'jobs',
  },
]

export default function OverviewPanel({ backendOk, jobs, onNavigate }) {
  const completed = jobs.filter(job => job.status === 'done').length
  const running = jobs.filter(job => job.status === 'running').length
  const failed = jobs.filter(job => job.status === 'error').length

  return (
    <div className="panel-stack overview-panel">
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
          <div className="overview-actions">
            <button className="action-button blue" type="button" onClick={() => onNavigate('policy')}>
              <Workflow size={18} />
              Start Policy Test
            </button>
            <button className="text-button" type="button" onClick={() => onNavigate('jobs')}>
              <CalendarDays size={17} />
              View Jobs
            </button>
          </div>
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

      <section className="overview-feature-grid" aria-label="Dashboard areas">
        {FEATURES.map(feature => (
          <FeatureCard key={feature.title} feature={feature} onNavigate={onNavigate} />
        ))}
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

function FeatureCard({ feature, onNavigate }) {
  const Icon = feature.icon

  return (
    <article className="overview-feature-card">
      <span className={`card-icon ${feature.color}`}>
        <Icon size={30} />
      </span>
      <h2>{feature.title}</h2>
      <p>{feature.copy}</p>
      <button className="text-button compact" type="button" onClick={() => onNavigate(feature.target)}>
        {feature.action}
      </button>
    </article>
  )
}
