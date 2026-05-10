import { useEffect, useMemo, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  BarChart2,
  Clipboard,
  Copy,
  Download,
  FileJson,
  Pencil,
  ShieldAlert,
  X,
} from 'lucide-react'

export default function ReportModal({ job, onClose }) {
  const ref = useRef(null)
  const [allureState, setAllureState] = useState('idle')
  const [allureError, setAllureError] = useState('')
  const [jsonEditorOpen, setJsonEditorOpen] = useState(false)
  const [editableJson, setEditableJson] = useState('')

  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdrop = e => { if (e.target === ref.current) onClose() }

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
      }
    } catch (error) {
      setAllureState('error')
      setAllureError(error?.message || 'Unable to contact dashboard backend')
    }
  }

  const isError = job.status === 'error'
  const duration = job.finished ? `${(job.finished - job.started).toFixed(2)}s` : 'Running'

  const allureLabel = {
    idle: 'Allure Report',
    generating: 'Generating…',
    ready: 'Open Again',
    error: 'Report Error',
  }[allureState]

  const report = useMemo(() => parsePolicyFlowReport(job.result || ''), [job.result])

  const copyReport = () => {
    if (report.profileJson) {
      navigator.clipboard.writeText(report.prettyProfileJson || report.profileJson)
    } else {
      const text = job.status === 'done' ? job.result : job.error
      navigator.clipboard.writeText(text || '')
    }
  }

  const openJsonEditor = () => {
    if (!jsonEditorOpen) {
      setEditableJson(report.prettyProfileJson || report.profileJson || '')
    }
    setJsonEditorOpen(v => !v)
  }

  const copyEditableJson = () => {
    navigator.clipboard.writeText(editableJson)
  }

  const hasStructuredReport = Boolean(
    report.profileJson || report.steps.length || Object.keys(report.summary).length || report.aiInsights.length
  )
  const isJson = job.status === 'done' && job.result?.trimStart().startsWith('{') && !hasStructuredReport
  const isMarkdown = !isError && !isJson && job.status === 'done'
  const isPersonaReport = Boolean(
    job.result?.includes('Generated Customer Profile') || job.result?.includes('Persona Variations')
  )
  const HeaderIcon = isError ? ShieldAlert : isJson ? FileJson : Clipboard

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
                <span className="report-badge neutral report-id-badge">
                  ID {job.id}
                </span>
              </div>
            </div>
          </div>

          <div className="report-actions">
            {isMarkdown && !isPersonaReport && (
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
            {report.profileJson && (
              <>
                <button onClick={openJsonEditor} className="text-button compact" type="button" title="View and edit profile JSON">
                  <Pencil size={16} />
                  {jsonEditorOpen ? 'Close Editor' : 'View & Edit'}
                </button>
                <button onClick={downloadProfile} className="text-button compact" type="button" title="Download profile JSON">
                  <Download size={16} />
                  Download
                </button>
              </>
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

        {jsonEditorOpen && (
          <div className="json-editor-panel">
            <div className="json-editor-toolbar">
              <span className="json-editor-label">Edit JSON</span>
              <button onClick={copyEditableJson} className="text-button compact" type="button">
                <Copy size={14} />
                Copy
              </button>
            </div>
            <textarea
              className="json-editor-textarea"
              value={editableJson}
              onChange={e => setEditableJson(e.target.value)}
              spellCheck={false}
            />
          </div>
        )}

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
            <StructuredPolicyReport job={job} report={report} />
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

function DocKV({ label, value }) {
  const v = (value === undefined || value === null) ? '' : String(value)
  if (v === '') return null
  return (
    <div className="doc-kv-row">
      <dt className="doc-kv-label">{label}</dt>
      <dd className="doc-kv-value">{v}</dd>
    </div>
  )
}

function StructuredPolicyReport({ job, report }) {
  const profile = useMemo(() => extractProfileData(report.profileJson), [report.profileJson])

  const statusLabel = job.status === 'done' ? 'Completed' : job.status === 'error' ? 'Failed' : 'Running'
  const dateStr = job.started
    ? new Date(job.started * 1000).toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit',
      })
    : '—'
  const duration = job.finished ? `${(job.finished - job.started).toFixed(2)}s` : '—'
  const shortId = (job.id || '').slice(0, 8)

  const hasPolicyDetails = profile && (
    profile.program || profile.effectiveDate || profile.paymentPlan || profile.maritalStatus ||
    profile.driverStatus || profile.employmentCategory || profile.occupation
  )
  const hasCustomerProfile = profile && (profile.firstName || profile.customerType || profile.email)

  return (
    <div className="doc-report">
      {/* Document header */}
      <div className="doc-head">
        <div className="doc-head-left">
          <div className="doc-title">{job.label}</div>
          <div className="doc-subtitle">EXECUTION REPORT</div>
        </div>
        <div className="doc-head-meta">
          {[
            { label: 'Execution ID', value: shortId },
            { label: 'Status', value: statusLabel },
            { label: 'Date', value: dateStr },
            { label: 'Duration', value: duration },
          ].map(({ label, value }) => (
            <div key={label} className="doc-meta-col">
              <div className="doc-meta-label">{label}</div>
              <div className="doc-meta-value">{value}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="doc-rule" />

      {/* Summary */}
      <div className="doc-section">
        <div className="doc-section-title">SUMMARY</div>
        <div className="doc-summary-layout">
          <dl className="doc-kv-list">
            <DocKV label="Policy" value={job.label} />
            <DocKV label="Policy Type" value={report.summary.lob} />
            <DocKV label="Execution Status" value={report.summary.status || statusLabel} />
            <DocKV label="Completed In" value={job.finished ? duration : undefined} />
            <DocKV label="Generated On" value={job.started ? dateStr : undefined} />
            <DocKV label="AI Prompt" value={report.sourceDescription} />
          </dl>
          {report.summary.premium && (
            <div className="doc-premium-box">
              <div className="doc-premium-label">PREMIUM</div>
              <div className="doc-premium-value">{report.summary.premium}</div>
            </div>
          )}
        </div>
      </div>

      {/* Policy Details + Customer Profile */}
      {(hasPolicyDetails || hasCustomerProfile) && (
        <>
          <div className="doc-rule" />
          <div className={hasPolicyDetails && hasCustomerProfile ? 'doc-two-col' : ''}>
            {hasPolicyDetails && (
              <div className="doc-section">
                <div className="doc-section-title">POLICY DETAILS</div>
                <dl className="doc-kv-list">
                  <DocKV label="Program" value={profile.program} />
                  <DocKV label="Effective Date" value={profile.effectiveDate} />
                  <DocKV label="Billing Method" value={profile.paymentPlan} />
                  <DocKV label="Marital Status" value={profile.maritalStatus} />
                  <DocKV label="Driver Status" value={profile.driverStatus} />
                  <DocKV label="Employment Category" value={profile.employmentCategory} />
                  <DocKV label="SR22" value={profile.sr22} />
                  <DocKV label="Occupation" value={profile.occupation} />
                  <DocKV label="Commercial Driver License" value={profile.commercialDriverLicense} />
                  <DocKV label="Prior Insurance" value={profile.priorInsurance} />
                  <DocKV label="Years Licensed" value={profile.yearsLicensed} />
                  <DocKV label="Accidents (3 Yrs)" value={profile.accidents3yr} />
                  <DocKV label="Violations (3 Yrs)" value={profile.violations3yr} />
                  <DocKV label="Claims (3 Yrs)" value={profile.claims3yr} />
                </dl>
              </div>
            )}
            {hasPolicyDetails && hasCustomerProfile && <div className="doc-col-divider" />}
            {hasCustomerProfile && (
              <div className="doc-section">
                <div className="doc-section-title">CUSTOMER PROFILE</div>
                <dl className="doc-kv-list">
                  <DocKV label="Customer Type" value={profile.customerType} />
                  <DocKV label="First Name" value={profile.firstName} />
                  <DocKV label="Last Name" value={profile.lastName} />
                  <DocKV label="DOB" value={profile.dob} />
                  <DocKV label="Phone" value={profile.phone} />
                  <DocKV label="Email" value={profile.email} />
                  <DocKV label="Address" value={profile.address} />
                  <DocKV label="ZIP" value={profile.zip} />
                  <DocKV label="State" value={profile.state} />
                  <DocKV label="City" value={profile.city} />
                  <DocKV label="Gender" value={profile.gender} />
                </dl>
              </div>
            )}
          </div>
        </>
      )}

      {/* Profile JSON fallback — shown when JSON couldn't be parsed into structured fields */}
      {report.profileJson && !hasPolicyDetails && !hasCustomerProfile && (
        <>
          <div className="doc-rule" />
          <div className="doc-section">
            <div className="doc-section-title">GENERATED CUSTOMER PROFILE</div>
            {report.sourceDescription && (
              <p className="doc-source-desc">{report.sourceDescription}</p>
            )}
            <div className="doc-json-shell">
              <pre className="json-code-viewer">{renderJsonSyntax(report.prettyProfileJson || report.profileJson)}</pre>
            </div>
          </div>
        </>
      )}

      <div className="doc-rule" />
      <div className="doc-footer">
        <span>Report generated on {dateStr}</span>
        <span>Page 1 of 1</span>
      </div>
    </div>
  )
}

/* ─── Parsers ─────────────────────────────────────────────────── */

function parsePolicyFlowReport(content) {
  const normalized = (content || '').replace(/\r\n/g, '\n').trim()
  if (!normalized) return emptyReport()

  if (normalized.startsWith('{')) {
    return {
      ...emptyReport(),
      profileJson: normalized,
      prettyProfileJson: formatPrettyJson(normalized),
    }
  }

  const chunks = normalized.split('\n\n---\n\n').map(chunk => chunk.trim()).filter(Boolean)
  const profileJson = extractProfileJson(chunks[0] || '')
  const summaryChunk = chunks[1] || ''
  const stepsChunk = chunks[2] || ''
  const uwChunk = chunks[3] || ''
  const errorChunk = chunks[4] || ''

  const summary = parseSummaryChunk(summaryChunk)
  const sourceDescription = extractSourceDescription(chunks[0] || '')
  const steps = parseStepsChunk(stepsChunk)
  const uwConditions = parseUwChunk(uwChunk)
  const coverageRows = parseCoverageRows(normalized)
  const error = parseErrorChunk(errorChunk)
  const prettyProfileJson = formatPrettyJson(profileJson)

  return {
    profileJson,
    prettyProfileJson,
    summary,
    sourceDescription,
    steps,
    uwConditions,
    coverageRows,
    error,
    screenshotPath: normalized.match(/Failure screenshot:\*\*\s*`([^`]+)`/i)?.[1] || '',
    aiInsights: [],
  }
}

function emptyReport() {
  return {
    profileJson: '',
    prettyProfileJson: '',
    summary: {},
    sourceDescription: '',
    steps: [],
    uwConditions: [],
    coverageRows: [],
    error: '',
    screenshotPath: '',
    aiInsights: [],
  }
}

function extractProfileJson(chunk) {
  const match = chunk.match(/```json\s*\n([\s\S]*?)\n```/i)
  return match?.[1]?.trim() || ''
}

function extractSourceDescription(chunk) {
  const match = chunk.match(/\*\*Source Description:\*\*\s*([^\n]+)/i)
  return cleanInline(match?.[1] || '').trim()
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

function parseCoverageRows(content) {
  const lines = content.split('\n')
  const rows = []
  let inTable = false
  let pastSeparator = false

  for (const rawLine of lines) {
    const line = rawLine.trim()
    if (!inTable) {
      if (/\|\s*Coverage\s*\|/i.test(line) && /Premium/i.test(line)) {
        inTable = true
        pastSeparator = false
      }
      continue
    }
    if (!pastSeparator) {
      if (/^\|\s*[-:]+/.test(line)) pastSeparator = true
      continue
    }
    if (!line.startsWith('|')) { inTable = false; continue }
    const cells = parseTableCells(line)
    if (cells.length < 2) continue
    const coverage = cleanInline(cells[0]).trim()
    if (!coverage) continue
    rows.push({
      coverage,
      limitDeductible: cells.length >= 3 ? cleanInline(cells[1]).trim() : '',
      premium: cleanInline(cells[cells.length - 1]).trim(),
      isTotal: /^total/i.test(coverage),
    })
  }
  return rows
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
  return { label: parts[0] || cleaned, detail: parts[1] || '' }
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
  const k = key.toLowerCase()
  if (k === 'lob') summary.lob = value
  else if (k === 'persona') summary.persona = value
  else if (k === 'status') summary.status = value
  else if (k === 'outcome') summary.outcome = value
  else if (k === 'total duration') summary.duration = value
  else if (k === 'premium') summary.premium = value
}

function formatPrettyJson(text) {
  if (!text) return ''
  try { return JSON.stringify(JSON.parse(text), null, 2) } catch { return text }
}

function sanitizeFilename(text) {
  return String(text || 'report')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

function extractProfileData(json) {
  if (!json) return null
  try {
    const p = JSON.parse(json)
    const get = (...keys) => {
      for (const k of keys) {
        const v = p[k]
        if (v !== undefined && v !== null && v !== '') return v
      }
      return undefined
    }
    const normBool = v => {
      if (v === true || v === 'true' || String(v).toLowerCase() === 'yes') return 'Yes'
      if (v === false || v === 'false' || String(v).toLowerCase() === 'no') return 'No'
      return v !== undefined ? String(v) : undefined
    }
    return {
      customerType: get('customer_type', 'CustomerType'),
      firstName: get('first_name', 'FirstName'),
      lastName: get('last_name', 'LastName'),
      dob: get('dob', 'DOB'),
      phone: get('phone', 'PhoneNum', 'phone_number'),
      email: get('email', 'Email'),
      address: get('address', 'Address'),
      zip: get('zip', 'ZIP'),
      state: get('state', 'State'),
      city: get('city', 'City'),
      gender: get('gender', 'Gender'),
      program: get('program', 'Program'),
      effectiveDate: get('effective_date', 'EffectiveDate'),
      paymentPlan: get('payment_plan', 'PaymentPlan'),
      maritalStatus: get('marital_status', 'MaritalStatus'),
      driverStatus: get('driver_status', 'DriverStatus'),
      employmentCategory: get('employment_category', 'EmploymentCategory'),
      sr22: normBool(get('sr22', 'SR22')),
      occupation: get('occupation', 'Occupation'),
      commercialDriverLicense: normBool(get('commercial_driver_license', 'CommercialDriverLicense')),
      priorInsurance: normBool(get('prior_insurance', 'PriorInsurance')),
      yearsLicensed: get('years_licensed', 'YearsLicensed'),
      accidents3yr: get('accidents_3yr', 'Accidents3Yr', 'accidents_3_years', 'accidents'),
      violations3yr: get('violations_3yr', 'Violations3Yr', 'violations_3_years', 'violations'),
      claims3yr: get('claims_3yr', 'Claims3Yr', 'claims_3_years', 'claims'),
    }
  } catch {
    return null
  }
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
