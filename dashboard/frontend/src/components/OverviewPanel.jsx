import {
  Activity,
  CalendarDays,
  CheckCircle2,
  Sparkles,
} from 'lucide-react'

export default function OverviewPanel({ backendOk, jobs, onOpenReport }) {
  const completed = jobs.filter(job => job.status === 'done').length
  const running = jobs.filter(job => job.status === 'running').length
  const failed = jobs.filter(job => job.status === 'error').length
  const feedItems = buildActivityFeed(jobs)

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
            INFORCE brings policy creation, live automation activity, and report viewing
            into a single dashboard for repeatable demos and faster QA feedback.
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

      <section className="activity-feed-panel" aria-label="Live activity feed">
        <div className="section-heading">
          <div>
            <span className="section-kicker">
              <Activity size={14} />
              Live Automation Activity Feed
            </span>
            <h2>What the dashboard is doing right now</h2>
          </div>
          <p>Recent automation runs appear here with short operational updates.</p>
        </div>

        <div className="activity-feed-list">
          {feedItems.length === 0 ? (
            <div className="empty-feed">
              <p>No runs yet.</p>
              <span>Launch a policy flow, UW audit, or batch run and the feed will populate here.</span>
            </div>
          ) : (
            feedItems.map((item, index) => (
              <ActivityCard key={`${item.title}-${item.id}`} item={item} index={index} onOpenReport={onOpenReport} />
            ))
          )}
        </div>
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

function ActivityCard({ item, index, onOpenReport }) {
  return (
    <article
      className={`activity-card ${index % 2 === 0 ? 'light' : 'dark'} ${item.status} ${index === 0 ? 'latest' : ''}`}
      style={{ animationDelay: `${index * 90}ms` }}
    >
      {item.canOpenReport && (
        <div className="activity-card-actions">
          <button
            className="text-button compact activity-report-button"
            type="button"
            onClick={() => onOpenReport?.(item.job)}
          >
            View report
          </button>
        </div>
      )}

      <div className="activity-card-top">
        <span className={`activity-dot ${item.status}`} />
        <span className="activity-status">{item.statusLabel}</span>
        <span className="activity-duration">{item.duration}</span>
      </div>

      <h3>{item.title}</h3>
      <p className="activity-terminal">{item.terminalLine}</p>

      <div className="activity-card-meta">
        <span>{item.meta}</span>
      </div>
    </article>
  )
}

function buildActivityFeed(jobs) {
  return jobs
    .slice()
    .sort((a, b) => (b.started || 0) - (a.started || 0))
    .slice(0, 6)
    .map((job, index) => {
      const label = job.label || 'Automation job'
      const lower = label.toLowerCase()
      const text = `${label} ${job.result || ''} ${job.error || ''}`.toLowerCase()
      const duration = formatDuration(elapsedSeconds(job))
      const started = formatStartedTime(job.started)
      const meta = `Started ${started} · ${job.id}`

      if (lower.includes('build profile')) {
        return {
          id: job.id,
          job,
          title: 'Generated customer profile',
          terminalLine: `> ${simplifyLabel(label)}`,
          status: job.status,
          statusLabel: statusLabel(job.status),
          duration,
          meta,
          canOpenReport: job.status !== 'running',
        }
      }

      if (lower.includes('rule test')) {
        const ruleId = extractRuleId(label, job.result)
        const title = ruleId ? `Executed UW Rule #${ruleId}` : 'Executed UW rule test'
        return {
          id: job.id,
          job,
          title,
          terminalLine: `> ${simplifyLabel(label)}`,
          status: job.status,
          statusLabel: statusLabel(job.status),
          duration,
          meta,
          canOpenReport: job.status !== 'running',
        }
      }

      if (lower.includes('batch test')) {
        const edgeCases = extractEdgeCases(job.result, job.error)
        return {
          id: job.id,
          job,
          title: edgeCases ? `${edgeCases} edge cases detected` : 'Batch scenario sweep completed',
          terminalLine: `> ${simplifyLabel(label)}`,
          status: job.status,
          statusLabel: statusLabel(job.status),
          duration,
          meta,
          canOpenReport: job.status !== 'running',
        }
      }

      if (lower.includes('uw audit')) {
        const edgeCases = extractEdgeCases(job.result, job.error)
        return {
          id: job.id,
          job,
          title: edgeCases ? `${edgeCases} edge cases detected` : 'Underwriting audit completed',
          terminalLine: `> ${simplifyLabel(label)}`,
          status: job.status,
          statusLabel: statusLabel(job.status),
          duration,
          meta,
          canOpenReport: job.status !== 'running',
        }
      }

      if (lower.includes('quick policy test') || lower.includes('policy journey')) {
        const isUwReferral = text.includes('uw referral') || text.includes('uw conditions triggered')
        const title = isUwReferral
          ? 'Referral triggered: review required'
          : job.status === 'running'
            ? 'Policy flow in progress'
            : job.status === 'error'
              ? 'Policy run failed'
              : 'Policy bound successfully'
        return {
          id: job.id,
          job,
          title,
          terminalLine: `> ${simplifyLabel(label)}`,
          status: job.status,
          statusLabel: isUwReferral ? 'uw referral' : statusLabel(job.status),
          duration,
          meta,
          canOpenReport: job.status !== 'running',
        }
      }

      return {
        id: job.id,
        job,
        title: job.status === 'running' ? 'Playwright session running' : job.status === 'error' ? 'Automation run failed' : 'Playwright session completed',
        terminalLine: `> ${simplifyLabel(label)}`,
        status: job.status,
        statusLabel: statusLabel(job.status),
        duration,
        meta,
        canOpenReport: job.status !== 'running',
      }
    })
}

function statusLabel(status) {
  if (status === 'done') return 'done'
  if (status === 'error') return 'error'
  return 'running'
}

function simplifyLabel(label) {
  return label.replace(/^Chat\s[–-]\s*/i, '').replace(/\s+/g, ' ').trim()
}

function elapsedSeconds(job) {
  const started = Number(job.started) || 0
  const finished = Number(job.finished) || Date.now() / 1000
  return Math.max(0, Math.round(finished - started))
}

function formatDuration(seconds) {
  const total = Math.max(0, Math.round(seconds))
  if (total < 60) return `${total}s`
  const minutes = Math.floor(total / 60)
  const secs = total % 60
  if (minutes < 60) return `${minutes}m ${String(secs).padStart(2, '0')}s`
  const hours = Math.floor(minutes / 60)
  const remMinutes = minutes % 60
  return `${hours}h ${String(remMinutes).padStart(2, '0')}m`
}

function formatStartedTime(started) {
  if (!started) return 'just now'
  return new Date(started * 1000).toLocaleTimeString(undefined, {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function extractRuleId(label, result) {
  const fromLabel = label.match(/Rule Test\s+[—-]\s+(.+)$/i)
  if (fromLabel?.[1]) return fromLabel[1].trim()

  const fromResult = result?.match(/Rule:\s*`([^`]+)`/i) || result?.match(/\|\s*\*\*Rule\*\*\s*\|\s*([^|]+)\|/i)
  return fromResult?.[1]?.trim() || ''
}

function extractEdgeCases(result, error) {
  const text = `${result || ''}\n${error || ''}`
  const critical = Number(text.match(/Critical violations \|\s*(\d+)/i)?.[1] || 0)
  const high = Number(text.match(/High severity \|\s*(\d+)/i)?.[1] || 0)
  const warning = Number(text.match(/Warnings \|\s*(\d+)/i)?.[1] || 0)
  const failed = Number(text.match(/Failed:\s*(\d+)/i)?.[1] || 0)
  const total = critical + high + warning + failed
  return total > 0 ? total : null
}
