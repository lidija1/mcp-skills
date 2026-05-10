import { useEffect, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  BarChart2,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clipboard,
  Clock3,
  Copy,
  Download,
  FileJson,
  ShieldAlert,
  Sparkles,
  X,
} from 'lucide-react'

export default function ReportModal({ job, onClose }) {
  const ref = useRef(null)
  const [allureState, setAllureState] = useState('idle') // idle | generating | ready | error
  const [allureError, setAllureError] = useState('')
  const [profileOpen, setProfileOpen] = useState(true)
  const [expandedStep, setExpandedStep] = useState(null)

  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdrop = e => { if (e.target === ref.current) onClose() }

  const copyReport = () => {
    const text = job.status === 'done' ? job.result : job.error
    navigator.clipboard.writeText(text || '')
  }

  const openAllure = async () => {
    setAllureState('generating')
    setAllureError('')
    try {
      const res = await fetch('http://localhost:8000/api/allure/generate', { method: 'POST' })
      const data = await res.json()
      if (data.ok) {
        setAllureState('ready')
        window.open('http://localhost:8000/allure/', '_blank')
      } else {
        setAllureState('error')
        setAllureError(data.error || 'Allure report generation failed')
        console.error('Allure generate failed:', data.error)
      }
    } catch (error) {
      setAllureState('error')
      setAllureError(error?.message || 'Unable to contact dashboard backend')
    }
  }

  const isJson = job.status === 'done' && job.result?.trimStart().startsWith('{')
  const isError = job.status === 'error'
  const isMarkdown = !isError && !isJson && job.status === 'done'
  const duration = job.finished ? `${Math.round(job.finished - job.started)}s` : 'Running'
  const HeaderIcon = isError ? ShieldAlert : isJson ? FileJson : Clipboard

  const allureLabel = {
    idle: 'Allure Report',
    generating: 'Generating…',
    ready: 'Open Again',
    error: 'Report Error',
  }[allureState]

  const report = useMemo(() => parsePolicyFlowReport(job.result || ''), [job.result])
  const hasStructuredReport = Boolean(
    report.profileJson || report.steps.length || Object.keys(report.summary).length || report.aiInsights.length
  )

  const copyProfile = async () => {
    if (!report.profileJson) return
    await navigator.clipboard.writeText(report.prettyProfileJson || report.profileJson)
  }

  const downloadProfile = () => {
    if (!report.profileJson) return
    const blob = new Blob([report.prettyProfileJson || report.profileJson], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${sanitizeFilename(job.label || 'policy-profile')}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div ref={ref} onClick={handleBackdrop} className="report-backdrop">
      <section className="report-dialog" role="dialog" aria-modal="true" aria-label="Job report">
        <header className="report-header">
          <div className="report-title-block">
            <div className={`report-icon ${isError ? 'error' : 'blue'}`}>
              <HeaderIcon size={24} />
            </div>
            <div className="report-title-copy">
              <h2>{job.label}</h2>
              <div className="report-header-badges">
                <span className={`report-badge ${job.status === 'done' ? 'success' : isError ? 'error' : 'running'}`}>
                  <span className="report-badge-dot" />
                  {isError ? 'Failed' : job.status === 'done' ? 'Completed' : 'Running'}
                </span>
                <span className="report-badge neutral">
                  <Clock3 size={13} />
                  {job.finished ? duration : 'Running'}
                </span>
                <span className="report-badge neutral report-id-badge">
                  ID {job.id}
                </span>
              </div>
            </div>
          </div>

          <div className="report-actions">
            {isMarkdown && (
              <button
                onClick={openAllure}
                className="text-button compact"
                type="button"
                disabled={allureState === 'generating'}
                title={allureState === 'error' ? allureError : 'Generate and open Allure report'}
              >
                <BarChart2 size={16} />
                {allureLabel}
              </button>
            )}
            <button onClick={copyReport} className="text-button compact" type="button">
              <Copy size={16} />
              Copy
            </button>
            <button onClick={onClose} className="modal-close-button" title="Close" aria-label="Close report" type="button">
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="report-body">
          {isError ? (
            <div className="report-state error">
              <div className="report-state-heading">
                <ShieldAlert size={21} />
                Error
              </div>
              <pre>{job.error}</pre>
            </div>
          ) : isJson ? (
            <div className="report-state json">
              <div className="report-state-heading">
                <FileJson size={21} />
                Generated Profile JSON
              </div>
              <pre>{JSON.stringify(JSON.parse(job.result), null, 2)}</pre>
            </div>
          ) : hasStructuredReport ? (
            <StructuredPolicyReport
              job={job}
              report={report}
              profileOpen={profileOpen}
              setProfileOpen={setProfileOpen}
              expandedStep={expandedStep}
              setExpandedStep={setExpandedStep}
              onCopyProfile={copyProfile}
              onDownloadProfile={downloadProfile}
            />
          ) : (
            <div className="markdown-report report-markdown">
              <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {job.result || ''}
              </Markdown>
            </div>
          )}
        </div>
        {!isError && job.result && <ViolationSummary content={job.result} />}
      </section>
    </div>
  )
}

function StructuredPolicyReport({
  job,
  report,
  profileOpen,
  setProfileOpen,
  expandedStep,
  setExpandedStep,
  onCopyProfile,
  onDownloadProfile,
}) {
  const heroTone = report.heroTone
  const heroIcon = heroTone === 'success' ? CheckCircle2 : heroTone === 'warning' ? ShieldAlert : Clock3
  const heroStatus = report.heroStatus
  const heroSubtitle = report.heroSubtitle
  const metrics = buildMetricCards(report, job)
  const replay = buildReplayStrip(report.steps)
  const insights = report.aiInsights

  return (
    <div className="report-story">
      <section className={`report-module report-hero-module ${heroTone}`}>
        <div className="report-hero-copy">
          <div className="report-hero-kicker">
            <Sparkles size={14} />
            Execution Story
          </div>
          <div className="report-hero-title-row">
            <div className="report-hero-icon">
              {heroTone === 'success' ? <CheckCircle2 size={30} /> : heroTone === 'warning' ? <ShieldAlert size={30} /> : <Clock3 size={30} />}
            </div>
            <div className="report-hero-text">
              <h3>{heroStatus}</h3>
              <p>{heroSubtitle}</p>
            </div>
          </div>
        </div>

        <div className="report-hero-stats">
          {report.summary.premium && (
            <div className="report-hero-premium">
              <span>Premium</span>
              <strong>{report.summary.premium}</strong>
            </div>
          )}
          <div className="report-hero-meta">
            <span>{report.summary.lob || 'Policy Run'}</span>
            <span>{report.summary.persona || 'Custom persona'}</span>
            <span>{report.summary.tcId || job.id}</span>
          </div>
        </div>
      </section>

      {report.profileJson && (
        <section className="report-module report-profile-module">
          <div className="report-module-header">
            <div>
              <span className="report-module-kicker">
                <Sparkles size={13} />
                AI Generated
              </span>
              <h4>Generated Customer Profile</h4>
            </div>

            <div className="report-module-actions">
              <button className="module-icon-button" type="button" onClick={onCopyProfile} title="Copy profile JSON">
                <Copy size={14} />
              </button>
              <button className="module-icon-button" type="button" onClick={onDownloadProfile} title="Download profile JSON">
                <Download size={14} />
              </button>
              <button className="module-icon-button toggle" type="button" onClick={() => setProfileOpen(open => !open)} aria-label="Toggle profile card">
                {profileOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </button>
            </div>
          </div>

          {profileOpen && (
            <div className="report-profile-code-shell">
              <div className="report-profile-code-title">Structured profile payload</div>
              <pre className="json-code-viewer">{renderJsonSyntax(report.prettyProfileJson || report.profileJson)}</pre>
            </div>
          )}
        </section>
      )}

      <section className="report-module">
        <div className="report-module-header">
          <div>
            <span className="report-module-kicker">Command Metrics</span>
            <h4>Execution summary</h4>
          </div>
        </div>
        <div className="report-metric-grid">
          {metrics.map(metric => (
            <MetricCard key={metric.label} {...metric} />
          ))}
        </div>
      </section>

      <section className="report-module">
        <div className="report-module-header">
          <div>
            <span className="report-module-kicker">Replay</span>
            <h4>Execution strip</h4>
          </div>
        </div>
        <div className="report-replay-strip" aria-label="Execution replay">
          {replay.map((step, index) => (
            <ReplayChip key={`${step.label}-${index}`} step={step} isLast={index === replay.length - 1} />
          ))}
        </div>
      </section>

      <section className="report-module">
        <div className="report-module-header">
          <div>
            <span className="report-module-kicker">Timeline</span>
            <h4>Step-by-step execution</h4>
          </div>
        </div>

        <div className="report-timeline">
          {report.steps.map((step, index) => (
            <StepTimelineItem
              key={`${step.label}-${index}`}
              step={step}
              index={index}
              expanded={expandedStep === index}
              onToggle={() => setExpandedStep(prev => (prev === index ? null : index))}
              isLast={index === report.steps.length - 1}
            />
          ))}
        </div>
      </section>

      {insights.length > 0 && (
        <section className="report-module report-insights-module">
          <div className="report-module-header">
            <div>
              <span className="report-module-kicker">AI Insights</span>
              <h4>What the run suggests</h4>
            </div>
          </div>
          <ul className="report-insights-list">
            {insights.map((insight, index) => (
              <li key={index}>{insight}</li>
            ))}
          </ul>
        </section>
      )}

      {report.uwConditions.length > 0 && (
        <section className="report-module">
          <div className="report-module-header">
            <div>
              <span className="report-module-kicker">UW Conditions</span>
              <h4>Triggered conditions</h4>
            </div>
          </div>
          <div className="report-uw-grid">
            {report.uwConditions.map((condition, index) => (
              <div className="report-uw-card" key={`${condition}-${index}`}>
                {condition}
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}

function MetricCard({ label, value, detail, tone = 'neutral' }) {
  return (
    <div className={`report-metric-card ${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      {detail && <p>{detail}</p>}
    </div>
  )
}

function ReplayChip({ step, isLast }) {
  return (
    <div className={`report-replay-chip ${step.tone}`}>
      <span>{step.label}</span>
      {!isLast && <i aria-hidden="true">→</i>}
    </div>
  )
}

function StepTimelineItem({ step, index, expanded, onToggle, isLast }) {
  return (
    <article className={`timeline-item ${step.tone} ${expanded ? 'expanded' : ''}`}>
      <div className="timeline-rail">
        <span className="timeline-dot" />
        {!isLast && <span className="timeline-line" />}
      </div>

      <div className="timeline-content">
        <button className="timeline-main" type="button" onClick={onToggle}>
          <div className="timeline-title-row">
            <span className="timeline-step-index">{String(index + 1).padStart(2, '0')}</span>
            <div>
              <h5>{step.label}</h5>
              {step.detail && <p>{step.detail}</p>}
            </div>
          </div>
          <div className="timeline-meta">
            <span className={`timeline-status ${step.tone}`}>{step.statusLabel}</span>
            <span className="timeline-duration">{step.duration}</span>
            <ChevronDown size={14} className={`timeline-toggle ${expanded ? 'open' : ''}`} />
          </div>
        </button>

        {expanded && step.notes && (
          <div className="timeline-notes">
            {step.notes.map((note, noteIndex) => (
              <div className="timeline-note" key={noteIndex}>
                {note}
              </div>
            ))}
          </div>
        )}
      </div>
    </article>
  )
}

function buildMetricCards(report, job) {
  return [
    { label: 'Policy Type', value: report.summary.lob || 'Unknown', tone: 'blue' },
    { label: 'Outcome', value: report.summary.outcome || 'Unknown', tone: report.heroTone },
    { label: 'Status', value: report.summary.status || 'Unknown', tone: report.heroTone },
    { label: 'Duration', value: report.summary.duration || (job.finished ? `${Math.round(job.finished - job.started)}s` : 'Running'), tone: 'purple' },
    { label: 'Persona', value: report.summary.persona || 'Custom', tone: 'neutral' },
    { label: 'TC ID', value: report.summary.tcId || job.id, tone: 'neutral' },
  ]
}

function buildReplayStrip(steps) {
  return steps.map(step => ({ label: step.shortLabel || step.label, tone: step.tone }))
}

function parsePolicyFlowReport(content) {
  const normalized = (content || '').replace(/\r\n/g, '\n').trim()
  if (!normalized) {
    return emptyReport()
  }

  const chunks = normalized.split('\n\n---\n\n').map(chunk => chunk.trim()).filter(Boolean)
  const profileJson = extractProfileJson(chunks[0] || '')
  const summaryChunk = chunks[1] || ''
  const stepsChunk = chunks[2] || ''
  const uwChunk = chunks[3] || ''
  const errorChunk = chunks[4] || ''
  const screenshotMatch = normalized.match(/Failure screenshot:\*\*\s*`([^`]+)`/i)

  const summary = parseSummaryChunk(summaryChunk)
  const steps = parseStepsChunk(stepsChunk)
  const uwConditions = parseUwChunk(uwChunk)
  const error = parseErrorChunk(errorChunk)
  const prettyProfileJson = formatPrettyJson(profileJson)
  const aiInsights = buildAiInsights(summary, steps, uwConditions, error)

  return {
    profileJson,
    prettyProfileJson,
    summary,
    steps,
    uwConditions,
    error,
    screenshotPath: screenshotMatch?.[1] || '',
    aiInsights,
    heroTone: deriveHeroTone(summary, error),
    heroStatus: deriveHeroStatus(summary, error),
    heroSubtitle: deriveHeroSubtitle(summary),
  }
}

function emptyReport() {
  return {
    profileJson: '',
    prettyProfileJson: '',
    summary: {},
    steps: [],
    uwConditions: [],
    error: '',
    screenshotPath: '',
    aiInsights: [],
    heroTone: 'neutral',
    heroStatus: 'Execution Story',
    heroSubtitle: 'No structured report data was detected.',
  }
}

function extractProfileJson(chunk) {
  const match = chunk.match(/```json\s*\n([\s\S]*?)\n```/i)
  return match?.[1]?.trim() || ''
}

function parseSummaryChunk(chunk) {
  if (!chunk) return {}

  const lines = chunk.split('\n').map(line => line.trimEnd())
  const headingLine = lines.find(line => line.startsWith('## '))
  const titleMatch = headingLine?.match(/^##\s+.*?—\s+`([^`]+)`/i)
  const summary = titleMatch ? { tcId: titleMatch[1] } : {}

  for (const line of lines) {
    if (!line.startsWith('|')) continue
    if (/^\|\s*-+/.test(line)) continue
    const cells = parseTableCells(line)
    if (cells.length < 2) continue
    const key = cleanInline(cells[0]).replace(/\*\*/g, '').trim()
    const value = cleanInline(cells[1]).trim()
    if (!key || key === '#' || key === '') continue
    assignSummaryField(summary, key, value)
  }

  return summary
}

function parseStepsChunk(chunk) {
  if (!chunk) return []

  const rows = chunk
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.startsWith('|') && !/^\|\s*#\s*\|/i.test(line) && !/^\|\s*-+/.test(line))

  const steps = []
  for (const row of rows) {
    const cells = parseTableCells(row)
    if (cells.length < 4) continue
    const { label, detail } = parseStepLabel(cells[1])
    steps.push({
      index: cells[0].trim(),
      label,
      shortLabel: shortenLabel(label),
      detail,
      statusLabel: cleanInline(cells[2]).trim(),
      duration: cleanInline(cells[3]).trim(),
      tone: inferStepTone(cells[2]),
      notes: detail ? [detail] : [],
    })
  }
  return steps
}

function parseUwChunk(chunk) {
  if (!chunk) return []

  const rows = chunk
    .split('\n')
    .map(line => line.trim())
    .filter(line => line.startsWith('|') && !/^\|\s*Type\s*\|/i.test(line) && !/^\|\s*-+/.test(line))

  return rows
    .map(row => parseTableCells(row))
    .filter(cells => cells.length >= 2)
    .map(cells => `${cleanInline(cells[0]).trim()} ${cleanInline(cells[1]).trim()}`.trim())
    .filter(Boolean)
}

function parseErrorChunk(chunk) {
  const match = chunk.match(/```([\s\S]*?)```/i)
  return match?.[1]?.trim() || ''
}

function parseTableCells(row) {
  return row
    .split('|')
    .map(cell => cell.trim())
    .filter((cell, index, arr) => !(index === 0 && cell === '') && !(index === arr.length - 1 && cell === ''))
}

function parseStepLabel(cell) {
  const withBreaks = cell.replace(/<br\s*\/?>/gi, '\n')
  const cleaned = cleanInline(withBreaks).replace(/\s+/g, ' ').trim()
  const parts = cleaned.split('\n').map(part => part.trim()).filter(Boolean)
  return {
    label: parts[0] || cleaned,
    detail: parts[1] || '',
  }
}

function shortenLabel(label) {
  return label
    .replace(/^Outcome:\s*/i, '')
    .replace(/^Chat\s[–-]\s*/i, '')
    .replace(/^Generated\s+/i, '')
    .trim()
    .split(/\s+/)
    .slice(0, 3)
    .join(' ')
}

function inferStepTone(statusCell) {
  const value = (statusCell || '').toLowerCase()
  if (value.includes('failed') || value.includes('error')) return 'error'
  if (value.includes('uw referral')) return 'warning'
  if (value.includes('passed')) return 'success'
  return 'neutral'
}

function cleanInline(text) {
  return String(text || '')
    .replace(/<\/?[^>]+>/g, '')
    .replace(/\*\*/g, '')
    .replace(/_/g, '')
    .replace(/`/g, '')
}

function assignSummaryField(summary, key, value) {
  const normalizedKey = key.toLowerCase()
  if (normalizedKey === 'lob') summary.lob = value
  else if (normalizedKey === 'persona') summary.persona = value
  else if (normalizedKey === 'status') summary.status = value
  else if (normalizedKey === 'outcome') summary.outcome = value
  else if (normalizedKey === 'total duration') summary.duration = value
  else if (normalizedKey === 'premium') summary.premium = value
}

function deriveHeroTone(summary, error) {
  const status = `${summary.status || ''} ${summary.outcome || ''} ${error || ''}`.toLowerCase()
  if (status.includes('failed') || status.includes('error')) return 'error'
  if (status.includes('uw referral')) return 'warning'
  return 'success'
}

function deriveHeroStatus(summary, error) {
  if (error) return 'EXECUTION FAILED'
  const outcome = `${summary.outcome || ''}`.toLowerCase()
  if (outcome.includes('policy bound')) return 'POLICY BOUND'
  if (outcome.includes('uw referral')) return 'UW REFERRAL'
  return 'EXECUTION COMPLETE'
}

function deriveHeroSubtitle(summary) {
  const lob = summary.lob || 'Policy Run'
  const duration = summary.duration || 'Running'
  return `${lob} • Completed in ${duration}`
}

function buildAiInsights(summary, steps, uwConditions, error) {
  const insights = []

  if (error) {
    insights.push('The execution ended early with an error state.')
  }

  if (!error && summary.outcome) {
    insights.push(`Outcome recorded as ${summary.outcome}.`)
  }

  if (!uwConditions.length && !`${summary.outcome || ''}`.toLowerCase().includes('uw referral')) {
    insights.push('No underwriting referral was triggered in this run.')
  }

  if (summary.premium) {
    insights.push(`Premium finalized at ${summary.premium}.`)
  }

  if (steps.length) {
    insights.push(`Execution moved through ${steps.length} timeline steps.`)
  }

  if (summary.duration) {
    insights.push(`Total execution time was ${summary.duration}.`)
  }

  if (uwConditions.length) {
    insights.push(`${uwConditions.length} underwriting condition(s) were captured.`)
  }

  return insights.slice(0, 4)
}

function formatPrettyJson(text) {
  if (!text) return ''
  try {
    return JSON.stringify(JSON.parse(text), null, 2)
  } catch {
    return text
  }
}

function sanitizeFilename(text) {
  return String(text || 'report')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function renderJsonSyntax(text) {
  const tokenRegex = /("(?:\\.|[^"\\])*"(?=\s*:)|"(?:\\.|[^"\\])*"|\btrue\b|\bfalse\b|\bnull\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[{}\[\],:])/g
  const nodes = []
  let lastIndex = 0
  let match

  while ((match = tokenRegex.exec(text))) {
    if (match.index > lastIndex) nodes.push(text.slice(lastIndex, match.index))
    const tokenEnd = match.index + match[0].length
    nodes.push(
      <span className={`json-token ${classifyJsonToken(match[0], text.slice(tokenEnd))}`} key={`${match.index}-${match[0]}`}>
        {match[0]}
      </span>
    )
    lastIndex = tokenRegex.lastIndex
  }

  if (lastIndex < text.length) nodes.push(text.slice(lastIndex))
  return nodes
}

function classifyJsonToken(token, trailingText = '') {
  if (token === '{' || token === '}' || token === '[' || token === ']' || token === ':' || token === ',') return 'punct'
  if (token === 'true' || token === 'false') return 'bool'
  if (token === 'null') return 'null'
  if (/^-?\d/.test(token)) return 'number'
  if (token.startsWith('"') && token.endsWith('"')) {
    return /^\s*:/.test(trailingText) ? 'key' : 'string'
  }
  return 'string'
}

const VIOLATION_TYPES = {
  FALSE_APPROVE: { label: 'False Approve', title: 'Rule engine missed a risk — risky profile was approved without referral' },
  FALSE_REFER: { label: 'False Refer', title: 'Rule engine over-triggered — clean profile was incorrectly flagged for review' },
  MISSING_CONDITION: { label: 'Missing Condition', title: 'Wrong or incomplete rule displayed on the UW referral page' },
  WRONG_COUNT: { label: 'Wrong Count', title: 'Fewer UW conditions appeared than expected' },
  EXTRA_CONDITIONS: { label: 'Extra Conditions', title: 'Unexpected additional rules fired that should not have triggered' },
  FLOW_ERROR: { label: 'Flow Error', title: 'Browser automation failed before a UW decision could be reached' },
}

function parseViolationTypes(content) {
  const results = []
  for (const line of content.split('\n')) {
    if (!line.startsWith('- ')) continue
    const parts = line.split('`')
    if (parts.length < 3) continue
    const type = parts[1]
    if (!/^[A-Z_]+$/.test(type) || type === 'PASS') continue
    const countMatch = parts[2].match(/:\s*(\d+)/)
    if (!countMatch) continue
    const count = parseInt(countMatch[1], 10)
    if (count > 0) results.push({ type, count })
  }
  return results
}

function ViolationSummary({ content }) {
  const violations = parseViolationTypes(content)
  if (!violations.length) return null
  return (
    <div className="violation-summary">
      <p className="violation-summary-title">Validation errors found</p>
      <ul className="violation-summary-list">
        {violations.map(v => {
          const meta = VIOLATION_TYPES[v.type]
          return (
            <li key={v.type}>
              <strong>{meta?.label || v.type}</strong>
              <span>{v.count}</span>
              {meta?.title && <em>{meta.title}</em>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

const mdComponents = {
  h1: ({ children }) => <h1>{children}</h1>,
  h2: ({ children }) => <h2>{children}</h2>,
  h3: ({ children }) => <h3>{children}</h3>,
  p: ({ children }) => <p>{children}</p>,
  strong: ({ children }) => <strong>{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  table: ({ children }) => (
    <div className="report-table-wrap">
      <table>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead>{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr>{children}</tr>,
  th: ({ children }) => <th>{children}</th>,
  td: ({ children }) => <td>{children}</td>,
  code: ({ children, className }) => {
    if (className) return <code className="code-block">{children}</code>
    return <code>{children}</code>
  },
  pre: ({ children }) => <pre>{children}</pre>,
  blockquote: ({ children }) => <blockquote>{children}</blockquote>,
  ul: ({ children }) => <ul>{children}</ul>,
  ol: ({ children }) => <ol>{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  hr: () => <hr />,
}
